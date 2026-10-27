"""Pure-pandas sales analytics (no UI imports)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def pkr(x: float) -> str:
    """Compact PKR label: 2.96M, 355.8K, 920."""
    if pd.isna(x):
        return "-"
    a = abs(x)
    if a >= 1e9:
        return f"PKR {x / 1e9:.2f}B"
    if a >= 1e6:
        return f"PKR {x / 1e6:.2f}M"
    if a >= 1e3:
        return f"PKR {x / 1e3:.1f}K"
    return f"PKR {x:,.0f}"


def summarize(df: pd.DataFrame, by, top: int | None = None, sort: str = "NetSales") -> pd.DataFrame:
    """Sales, discount, volume and average basket per group."""
    g = df.groupby(by, observed=True).agg(
        NetSales=("NetSales", "sum"), GrossSales=("GrossSales", "sum"), DiscountAmt=("DiscountAmt", "sum"),
        Transactions=("TransactionID", "count"), Units=("Quantity", "sum"))
    g["AvgTicket"] = g["NetSales"] / g["Transactions"]
    g["DiscountPct"] = g["DiscountAmt"] / g["GrossSales"]
    g["Share"] = g["NetSales"] / g["NetSales"].sum() if g["NetSales"].sum() else np.nan
    g = g.reset_index()
    if sort:
        g = g.sort_values(sort, ascending=False)
    if top:
        g = g.head(top)
    return g.reset_index(drop=True)


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    m = summarize(df, "YearMonth", sort=None).sort_values("YearMonth").reset_index(drop=True)
    m["MA3"] = m["NetSales"].rolling(3, min_periods=1).mean()
    m["Year"] = m["YearMonth"].dt.year.astype(str)
    m["Month"] = m["YearMonth"].dt.month_name()
    return m


def pivot_sum(df: pd.DataFrame, rows: str, cols: str, value: str = "NetSales") -> pd.DataFrame:
    p = df.pivot_table(index=rows, columns=cols, values=value, aggfunc="sum", observed=True)
    p.index = p.index.astype(str)
    p.columns = p.columns.astype(str)
    p.index.name, p.columns.name = rows, cols
    return p


def pareto(df: pd.DataFrame, by: str) -> pd.DataFrame:
    s = summarize(df, by)[[by, "NetSales"]]
    s["CumShare"] = s["NetSales"].cumsum() / s["NetSales"].sum()
    return s


def yearly(df: pd.DataFrame) -> pd.DataFrame:
    y = summarize(df, "Year", sort=None).sort_values("Year").reset_index(drop=True)
    y["Growth"] = y["NetSales"].pct_change()
    y["Year"] = y["Year"].astype(str)
    return y


def kpis(df: pd.DataFrame) -> dict:
    net, gross = df["NetSales"].sum(), df["GrossSales"].sum()
    disc = df["DiscountAmt"].sum()
    d = df[df["Discounted"]]
    return {
        "net": net, "gross": gross, "discount": disc, "disc_pct": disc / gross if gross else np.nan,
        "txns": len(df), "units": int(df["Quantity"].sum()), "avg_ticket": net / len(df) if len(df) else np.nan,
        "disc_rate": df["Discounted"].mean() if len(df) else np.nan,
        "avg_disc_when": d["DiscountPct"].mean() if len(d) else np.nan,
    }


def key_insights(df: pd.DataFrame, min_n: int = 20) -> list[str]:
    if len(df) < min_n:
        return ["Not enough transactions in the current selection for reliable insights."]
    out = []
    k = kpis(df)
    out.append(f"**{pkr(k['net'])}** net sales from **{k['txns']:,}** transactions "
               f"(average basket **{pkr(k['avg_ticket'])}**).")
    cat = summarize(df, "Category")
    t = cat.iloc[0]
    out.append(f"**{t['Category']}** is the biggest category: **{t['Share']:.0%}** of net sales from only "
               f"**{t['Transactions'] / len(df):.0%}** of transactions.")
    br = summarize(df, "Branch")
    if len(br) > 1:
        out.append(f"**{br.iloc[0]['Branch']}** leads branches with **{pkr(br.iloc[0]['NetSales'])}** "
                   f"({br.iloc[0]['Share']:.0%}); **{br.iloc[-1]['Branch']}** is lowest at "
                   f"**{pkr(br.iloc[-1]['NetSales'])}**.")
    y = yearly(df)
    if len(y) >= 2 and pd.notna(y.iloc[-1]["Growth"]):
        a, b = y.iloc[-1], y.iloc[-2]
        out.append(f"**{a['Year']}** net sales are **{abs(a['Growth']):.1%} "
                   f"{'higher' if a['Growth'] >= 0 else 'lower'}** than {b['Year']} "
                   f"({pkr(a['NetSales'])} vs {pkr(b['NetSales'])}).")
    m = summarize(df, "Month", sort=None)
    if len(m) > 2:
        out.append(f"Strongest calendar month is **{m.loc[m['NetSales'].idxmax(), 'Month']}**, "
                   f"weakest is **{m.loc[m['NetSales'].idxmin(), 'Month']}** (all years combined).")
    out.append(f"**{k['disc_rate']:.0%}** of transactions carry a discount (avg **{k['avg_disc_when']:.1%}** when applied), "
               f"giving up **{pkr(k['discount'])}** = **{k['disc_pct']:.1%}** of gross sales.")
    p = summarize(df, "Product", top=1).iloc[0]
    out.append(f"Top product by revenue: **{p['Product']}** ({pkr(p['NetSales'])}, {int(p['Units'])} units).")
    top10 = df["NetSales"].nlargest(max(1, int(len(df) * .1))).sum() / k["net"]
    out.append(f"The top 10% of transactions generate **{top10:.0%}** of net sales — revenue is concentrated in high-ticket items.")
    return out
