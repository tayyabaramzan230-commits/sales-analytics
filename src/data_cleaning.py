"""Load, validate, clean and enrich the sales dataset. `clean()` also returns an audit log."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RENAME = {"Transaction ID": "TransactionID", "Product Name": "Product", "Unit Price (PKR)": "UnitPrice",
          "Gross Sales (PKR)": "GrossSales", "Discount %": "DiscountPct",
          "Discount Amount (PKR)": "DiscountAmt", "Net Sales (PKR)": "NetSales"}
REQUIRED = ["TransactionID", "Date", "Branch", "Category", "Subcategory", "Product", "Quantity",
            "UnitPrice", "GrossSales", "DiscountPct", "DiscountAmt", "NetSales"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DISC_LABELS = ["No discount", "Up to 5%", "5-10%", "10-20%", "Over 20%"]
TICKET_LABELS = ["Under 1k", "1k-5k", "5k-20k", "Over 20k"]


def load_raw(src) -> pd.DataFrame:
    name = str(getattr(src, "name", src)).lower()
    return pd.read_csv(src) if name.endswith(".csv") else pd.read_excel(src)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log: list[dict] = []

    def add(step, issue, action, n):
        log.append({"Step": step, "Issue found": issue, "Action taken": action, "Rows affected": n})

    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns=RENAME)
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    add("Schema", "Column names contain spaces/units, e.g. 'Net Sales (PKR)'",
        "Renamed to compact names (NetSales, UnitPrice, ...); all amounts are PKR", len(RENAME))

    # whitespace in text columns
    n_ws = 0
    for c in [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])
              and not pd.api.types.is_datetime64_any_dtype(df[c])]:
        s = df[c].astype("string")
        t = s.str.strip()
        n_ws += int((s != t).fillna(False).sum())
        df[c] = t.astype(object)
    add("Whitespace", "Leading/trailing spaces in text fields", "Trimmed", n_ws)

    # types
    d = pd.to_datetime(df["Date"], errors="coerce")
    bad_dates = int(d.isna().sum())
    df["Date"] = d
    for c in ["Quantity", "UnitPrice", "GrossSales", "DiscountPct", "DiscountAmt", "NetSales"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    add("Data types", "Dates / numeric fields parsed", "Converted; unparseable values become missing", bad_dates)

    # duplicates & missing
    n_exact = int(df.duplicated().sum())
    df = df.drop_duplicates()
    n_id = int(df["TransactionID"].duplicated().sum())
    df = df.drop_duplicates(subset="TransactionID", keep="first")
    add("Duplicates", "Exact duplicate rows / repeated TransactionID", "Removed (first kept)", n_exact + n_id)
    key_na = df[REQUIRED].isna().any(axis=1)
    add("Missing values", "Rows missing a required field", "Dropped" if key_na.any() else "None found",
        int(key_na.sum()))
    df = df[~key_na]
    for c in ["Branch", "Category", "Subcategory", "Product"]:
        df[c] = df[c].astype(str)

    # arithmetic integrity (repair by recomputation when needed)
    bad_gross = (df["GrossSales"] - df["Quantity"] * df["UnitPrice"]).abs() > 0.01
    df.loc[bad_gross, "GrossSales"] = df["Quantity"] * df["UnitPrice"]
    bad_disc = (df["DiscountAmt"] - df["GrossSales"] * df["DiscountPct"]).abs() > 1
    df.loc[bad_disc, "DiscountAmt"] = (df["GrossSales"] * df["DiscountPct"]).round(2)
    bad_net = (df["NetSales"] - (df["GrossSales"] - df["DiscountAmt"])).abs() > 0.01
    df.loc[bad_net, "NetSales"] = df["GrossSales"] - df["DiscountAmt"]
    for name, bad in [("GrossSales = Quantity x UnitPrice", bad_gross),
                      ("DiscountAmt = GrossSales x Discount %", bad_disc),
                      ("NetSales = GrossSales - DiscountAmt", bad_net)]:
        add("Validation", f"Rule: {name}", "Passed" if bad.sum() == 0 else "Recomputed", int(bad.sum()))
    nonpos = int(((df["Quantity"] <= 0) | (df["UnitPrice"] <= 0) | (df["NetSales"] <= 0)).sum())
    add("Validation", "Non-positive quantity / price / net sales", "Passed" if nonpos == 0 else "Flagged", nonpos)
    bad_rate = int(((df["DiscountPct"] < 0) | (df["DiscountPct"] > 1)).sum())
    add("Validation", "Discount % outside 0-100%", "Passed" if bad_rate == 0 else "Flagged", bad_rate)

    # calendar fields derived from Date (single source of truth)
    ym_bad = int(((df.get("Year", df["Date"].dt.year) != df["Date"].dt.year)
                  | (df.get("Month", df["Date"].dt.month_name()) != df["Date"].dt.month_name())).sum())
    df["Year"] = df["Date"].dt.year.astype(int)
    df["Month"] = pd.Categorical(df["Date"].dt.month_name(), MONTHS, ordered=True)
    add("Validation", "Year / Month columns agree with Date", "Passed" if ym_bad == 0 else "Re-derived", ym_bad)
    city = df["Branch"].str.split(" - ").str[0].str.strip()
    city_bad = int((df["City"].astype(str).str.strip() != city).sum()) if "City" in df else 0
    df["City"] = city
    df["BranchShort"] = df["Branch"].str.split(" - ").str[-1].str.strip()
    add("Validation", "City agrees with Branch", "Passed" if city_bad == 0 else "Re-derived", city_bad)
    hier = int((df.groupby("Product")["Subcategory"].nunique() > 1).sum()
               + (df.groupby("Subcategory")["Category"].nunique() > 1).sum())
    add("Validation", "Product > Subcategory > Category hierarchy is consistent",
        "Passed" if hier == 0 else "Flagged", hier)

    # price consistency (reported only)
    pr = df.groupby("Product")["UnitPrice"].agg(["min", "max"])
    wild = int(((pr["max"] / pr["min"]) > 5).sum())
    add("Data quality flag",
        f"Unit price varies more than 5x within the same product for {wild} of {len(pr)} products "
        "(e.g. one 'Smartphone 64GB' sells at PKR 5,000 and PKR 84,000)",
        "Kept as recorded; analysis focuses on revenue by category/branch/time rather than SKU price. "
        "Worth checking at the source.", wild)

    # outliers within category (IQR) - reported only
    q = df.groupby("Category")["NetSales"].transform
    q1, q3 = q(lambda s: s.quantile(.25)), q(lambda s: s.quantile(.75))
    out = int((df["NetSales"] > q3 + 1.5 * (q3 - q1)).sum())
    add("Outliers", "Transactions above 1.5xIQR of their category's net sales", "Retained (genuine large baskets)", out)

    # features
    df["MonthNum"] = df["Date"].dt.month
    df["YearMonth"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    df["Quarter"] = "Q" + df["Date"].dt.quarter.astype(str)
    df["Weekday"] = pd.Categorical(df["Date"].dt.day_name(), WEEKDAYS, ordered=True)
    df["IsWeekend"] = df["Date"].dt.dayofweek >= 5
    df["Discounted"] = df["DiscountPct"] > 0
    df["DiscountBand"] = pd.cut(df["DiscountPct"], [-1, 0, .05, .10, .20, 1.0], labels=DISC_LABELS)
    df["TicketBand"] = pd.cut(df["NetSales"], [0, 1000, 5000, 20000, np.inf], labels=TICKET_LABELS, right=False)
    add("Feature engineering", "Derived: YearMonth, Quarter, Weekday, IsWeekend, Discounted, DiscountBand, TicketBand, BranchShort",
        "Added", 8)

    out_df = df.sort_values(["Date", "TransactionID"]).reset_index(drop=True)
    return out_df, pd.DataFrame(log)


def load_and_clean(src):
    raw = load_raw(src)
    df, log = clean(raw)
    return raw, df, log


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    raw, df, log = load_and_clean(root / "data" / "raw" / "Sales.xlsx")
    (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
    df.to_csv(root / "data" / "processed" / "Sales_clean.csv", index=False)
    log.to_csv(root / "data" / "processed" / "cleaning_log.csv", index=False)
    print(raw.shape, "->", df.shape)
    print(log[["Step", "Issue found", "Rows affected"]].to_string(index=False, max_colwidth=90))
