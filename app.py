"""Sales Analytics - interactive Streamlit dashboard."""
from __future__ import annotations

import datetime as dt
import inspect
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src import analysis as an
from src import charts as ch
from src.analysis import pkr
from src.data_cleaning import MONTHS, load_and_clean

BASE = Path(__file__).parent
DATA_PATH = BASE / "data" / "raw" / "Sales.xlsx"

st.set_page_config(page_title="Sales Analytics Dashboard", page_icon="🛒", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1400px;}
.hero {background: linear-gradient(120deg,#0F766E 0%,#2563EB 60%,#7C3AED 100%);
       border-radius: 18px; padding: 26px 32px; color:#fff; margin-bottom: 18px;}
.hero h1 {color:#fff; margin:0; font-size:2rem; font-weight:800; letter-spacing:-.5px;}
.hero p {color:#DBEAFE; margin:6px 0 0 0; font-size:1rem;}
.kpi {background:#fff; border:1px solid #E5E7EB; border-radius:14px; padding:16px 18px;
      box-shadow:0 1px 3px rgba(17,24,39,.06); border-left:5px solid var(--accent,#0F766E);}
.kpi .label {font-size:.76rem; text-transform:uppercase; letter-spacing:.06em; color:#6B7280; font-weight:600;}
.kpi .value {font-size:1.65rem; font-weight:800; color:#111827; line-height:1.25;}
.kpi .sub {font-size:.8rem; color:#6B7280;}
.insight {background:#fff; border:1px solid #E5E7EB; border-radius:12px; padding:10px 16px; margin-bottom:8px;
          border-left:4px solid #0F766E; color:#1F2937;}
.section {font-size:1.15rem; font-weight:700; color:#111827; margin: 8px 0 2px 0;}
.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [data-baseweb="tab"] {background:#fff; border-radius:10px 10px 0 0; padding:8px 16px; border:1px solid #E5E7EB;}
.stTabs [aria-selected="true"] {background:#CCFBF1; color:#115E59; font-weight:700;}
</style>
""", unsafe_allow_html=True)


def _stretch(fn) -> dict:
    """Full-width kwarg that works on older and newer Streamlit releases."""
    params = inspect.signature(fn).parameters
    if fn is st.plotly_chart:
        return {"width": "stretch"} if "width" in params else {"use_container_width": True}
    return {"use_container_width": True} if "use_container_width" in params else {"width": "stretch"}


def show(fig):
    show.n += 1
    st.plotly_chart(fig, key=f"chart_{show.n}", **_stretch(st.plotly_chart))


show.n = 0


def table(df: pd.DataFrame, **kw):
    st.dataframe(df, hide_index=True, **_stretch(st.dataframe), **kw)


def kpi(col, label, value, sub="", accent="#0F766E"):
    col.markdown(f'<div class="kpi" style="--accent:{accent}"><div class="label">{label}</div>'
                 f'<div class="value">{value}</div><div class="sub">{sub}&nbsp;</div></div>',
                 unsafe_allow_html=True)


def section(text):
    st.markdown(f'<div class="section">{text}</div>', unsafe_allow_html=True)


def fmt_table(df: pd.DataFrame) -> pd.DataFrame:
    """Human-friendly numbers for display tables."""
    out = df.copy()
    for c in ["NetSales", "GrossSales", "DiscountAmt", "AvgTicket"]:
        if c in out:
            out[c] = out[c].round(0).astype(int)
    for c in ["Share", "DiscountPct"]:
        if c in out:
            out[c] = (out[c] * 100).round(1)
    return out.rename(columns={"Share": "Share %", "DiscountPct": "Discount %"})


@st.cache_data(show_spinner="Cleaning data...")
def get_data(source):
    return load_and_clean(source)


# ------------------------------------------------------------------ data load
with st.sidebar:
    st.markdown("## 🛒 Sales Analytics")
    upload = st.file_uploader("Use your own file (same columns)", type=["xlsx", "xls", "csv"])
try:
    raw, df_all, clean_log = get_data(upload if upload is not None else DATA_PATH)
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not load the data: {exc}")
    st.stop()

# -------------------------------------------------------------------- filters
D_MIN, D_MAX = df_all["Date"].min().date(), df_all["Date"].max().date()
BR = sorted(df_all["Branch"].unique())
CATS = sorted(df_all["Category"].unique())
DISC_OPTS = ["All", "Discounted only", "Full price only"]


def reset_filters():
    st.session_state["f_dates"] = (D_MIN, D_MAX)
    st.session_state["f_branch"] = BR
    st.session_state["f_cat"] = CATS
    st.session_state["f_sub"] = []
    st.session_state["f_disc"] = "All"


with st.sidebar:
    st.markdown("### 🎛️ Filters")
    st.button("↺ Reset filters", on_click=reset_filters)
    dates = st.date_input("Date range", value=(D_MIN, D_MAX), min_value=D_MIN, max_value=D_MAX, key="f_dates")
    branches = st.multiselect("Branch", BR, default=BR, key="f_branch")
    cats = st.multiselect("Category", CATS, default=CATS, key="f_cat")
    subs_all = sorted(df_all[df_all["Category"].isin(cats)]["Subcategory"].unique())
    st.session_state["f_sub"] = [x for x in st.session_state.get("f_sub", []) if x in subs_all]
    subs = st.multiselect("Subcategory (optional)", subs_all, default=[], key="f_sub",
                          help="Leave empty to include every subcategory.")
    disc = st.radio("Discount", DISC_OPTS, key="f_disc", horizontal=False)

if isinstance(dates, (tuple, list)) and len(dates) == 2:
    d0, d1 = dates
elif isinstance(dates, (tuple, list)) and len(dates) == 1:
    d0 = d1 = dates[0]
else:
    d0 = d1 = dates
if not isinstance(d0, dt.date):
    d0, d1 = D_MIN, D_MAX

mask = df_all["Date"].dt.date.between(d0, d1) & df_all["Branch"].isin(branches) & df_all["Category"].isin(cats)
if subs:
    mask &= df_all["Subcategory"].isin(subs)
if disc == "Discounted only":
    mask &= df_all["Discounted"]
elif disc == "Full price only":
    mask &= ~df_all["Discounted"]
df = df_all[mask]

with st.sidebar:
    st.markdown("---")
    st.caption(f"Showing **{len(df):,}** of **{len(df_all):,}** transactions")
    st.caption("All amounts in PKR")

# ----------------------------------------------------------------------- hero
st.markdown("""<div class="hero"><h1>🛒 Sales Analytics Dashboard</h1>
<p>Revenue, products, branches and discounts across four cities — from raw transactions to decisions.</p></div>""",
            unsafe_allow_html=True)

if df.empty:
    st.warning("No transactions match the current filters. Adjust or reset them in the sidebar.")
    st.stop()
if len(df) < 30:
    st.info("Fewer than 30 transactions selected — treat the numbers with caution.")

# ----------------------------------------------------------------------- KPIs
k = an.kpis(df)
yr = an.yearly(df)
growth_txt = ""
if len(yr) >= 2 and pd.notna(yr.iloc[-1]["Growth"]):
    growth_txt = f"{yr.iloc[-1]['Year']} vs {yr.iloc[-2]['Year']}: {yr.iloc[-1]['Growth']:+.1%}"
c = st.columns(6)
kpi(c[0], "Net sales", pkr(k["net"]), growth_txt or "&nbsp;", "#0F766E")
kpi(c[1], "Transactions", f"{k['txns']:,}", f"{k['units']:,} units sold", "#2563EB")
kpi(c[2], "Avg basket", pkr(k["avg_ticket"]), "net sales per transaction", "#7C3AED")
kpi(c[3], "Gross sales", pkr(k["gross"]), "before discounts", "#64748B")
kpi(c[4], "Discounts given", pkr(k["discount"]), f"{k['disc_pct']:.1%} of gross", "#E11D48")
kpi(c[5], "Discounted txns", f"{k['disc_rate']:.0%}", f"avg depth {k['avg_disc_when']:.1%}" if k["disc_rate"] else "", "#F59E0B")
st.write("")

tabs = st.tabs(["🏠 Overview", "📈 Trends", "📦 Products", "🏬 Branches", "🏷️ Discounts",
                "🧾 Transactions", "🗂️ Data & quality"])

# ------------------------------------------------------------------- Overview
with tabs[0]:
    section("Key findings (update with your filters)")
    for line in an.key_insights(df):
        st.markdown(f'<div class="insight">{line}</div>', unsafe_allow_html=True)
    st.write("")
    a, b = st.columns(2)
    cat = an.summarize(df, "Category")
    with a:
        show(ch.donut(cat, "Category", "NetSales", "Net sales share by category"))
    with b:
        show(ch.bar(an.summarize(df, "Branch"), "Branch", "NetSales", "Net sales by branch", horizontal=True))
    show(ch.monthly_bars(an.monthly(df), "Monthly net sales with 3-month average"))
    show(ch.treemap(an.summarize(df, ["Category", "Subcategory"]), ["Category", "Subcategory"], "NetSales",
                    "Where the revenue comes from: category → subcategory"))

# --------------------------------------------------------------------- Trends
with tabs[1]:
    m = an.monthly(df)
    a, b = st.columns(2)
    with a:
        show(ch.year_lines(m, "Seasonality: monthly net sales by year"))
    with b:
        show(ch.bar(yr, "Year", "NetSales", "Net sales by year"))
    a, b = st.columns(2)
    with a:
        show(ch.heatmap(an.pivot_sum(df, "Year", "Month").reindex(columns=[x for x in MONTHS if x in df["Month"].astype(str).unique()]),
                        "Net sales heatmap: year × month", height=300))
    with b:
        q = an.summarize(df.assign(YearQ=df["Year"].astype(str) + " " + df["Quarter"]), "YearQ", sort=None).sort_values("YearQ")
        show(ch.bar(q, "YearQ", "NetSales", "Net sales by quarter", height=300))
    a, b = st.columns(2)
    with a:
        wd = an.summarize(df, "Weekday", sort=None)
        show(ch.bar(wd, "Weekday", "NetSales", "Net sales by weekday", height=340))
    with b:
        show(ch.bar(wd, "Weekday", "Transactions", "Transactions by weekday", fmt=",d", height=340))
    section("Monthly detail")
    table(fmt_table(m[["YearMonth", "NetSales", "Transactions", "Units", "AvgTicket", "DiscountPct"]]
                    .assign(YearMonth=m["YearMonth"].dt.strftime("%b %Y"))))

# ------------------------------------------------------------------- Products
with tabs[2]:
    a, b = st.columns(2)
    cat = an.summarize(df, "Category")
    with a:
        show(ch.bar(cat, "Category", "NetSales", "Net sales by category", horizontal=True, height=380))
    with b:
        show(ch.bar(cat.sort_values("AvgTicket", ascending=False), "Category", "AvgTicket",
                    "Average basket by category", horizontal=True, height=380))
    show(ch.pareto(an.pareto(df, "Subcategory"), "Subcategory", "Pareto: subcategories ranked by net sales"))
    section("Top products")
    x1, x2 = st.columns([1, 3])
    metric = x1.radio("Rank by", ["NetSales", "Units", "Transactions"], format_func=lambda v: ch.LABELS.get(v, v))
    topn = x1.slider("How many", 5, 30, 12)
    with x2:
        tp = an.summarize(df, ["Product", "Category"], sort=metric, top=topn)
        show(ch.bar(tp, "Product", metric, f"Top {topn} products by {ch.LABELS.get(metric, metric).lower()}",
                    horizontal=True, color="Category", height=max(380, 30 * topn), stack=True))
    show(ch.heatmap(an.pivot_sum(df, "Category", "Branch"), "Net sales: category × branch", height=380))
    section("Subcategory table")
    table(fmt_table(an.summarize(df, ["Category", "Subcategory"])))
    st.caption("Note: unit prices for the same product vary widely in the source data, so product-level "
               "price comparisons are not reliable — revenue rankings are.")

# ------------------------------------------------------------------- Branches
with tabs[3]:
    br = an.summarize(df, "Branch")
    a, b, cc = st.columns(3)
    with a:
        show(ch.bar(br, "Branch", "NetSales", "Net sales", horizontal=True, height=300))
    with b:
        show(ch.bar(br, "Branch", "Transactions", "Transactions", horizontal=True, fmt=",d", height=300))
    with cc:
        show(ch.bar(br, "Branch", "AvgTicket", "Average basket", horizontal=True, height=300))
    bm = df.groupby(["YearMonth", "Branch"], observed=True)["NetSales"].sum().reset_index()

    fig = px.line(bm, x="YearMonth", y="NetSales", color="Branch", color_discrete_sequence=ch.SEQ, labels=ch.LABELS)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    show(ch.style(fig, "Monthly net sales by branch", 380))
    a, b = st.columns(2)
    with a:
        show(ch.heatmap(an.pivot_sum(df, "Branch", "Category"), "Net sales: branch × category", height=360))
    with b:
        mix = an.summarize(df, ["Branch", "Category"], sort=None)
        show(ch.bar(mix, "Branch", "NetSales", "Category mix by branch", color="Category", stack=True,
                    height=360))
    section("Branch scorecard")
    table(fmt_table(br))

# ------------------------------------------------------------------ Discounts
with tabs[4]:
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Discounted share", f"{k['disc_rate']:.0%}", "of transactions", "#F59E0B")
    kpi(c2, "Avg discount depth", f"{k['avg_disc_when']:.1%}" if pd.notna(k["avg_disc_when"]) else "-",
        "when a discount applies", "#E11D48")
    kpi(c3, "Revenue given up", pkr(k["discount"]), "total discount amount", "#7C3AED")
    kpi(c4, "Discount / gross", f"{k['disc_pct']:.1%}", "effective rate", "#2563EB")
    st.write("")
    dd = df[df["Discounted"]]
    a, b = st.columns(2)
    with a:
        if len(dd):
            show(ch.hist(dd.assign(DiscountPct=dd["DiscountPct"] * 100), "DiscountPct",
                         "Discount depth distribution (%, discounted transactions)", nbins=20))
        else:
            st.info("No discounted transactions in the current selection.")
    with b:
        band = an.summarize(df, "DiscountBand", sort=None)
        show(ch.bar(band, "DiscountBand", "Transactions", "Transactions by discount band", fmt=",d"))
    a, b = st.columns(2)
    cd = df.groupby("Category", observed=True).agg(DiscountedShare=("Discounted", "mean")).reset_index()
    with a:
        show(ch.bar(cd.sort_values("DiscountedShare", ascending=False), "Category", "DiscountedShare",
                    "Share of transactions discounted, by category", horizontal=True, fmt=".0%"))
    with b:
        cc_ = an.summarize(df, "Category", sort="DiscountAmt")
        show(ch.bar(cc_, "Category", "DiscountAmt", "Discount amount (PKR) by category", horizontal=True))
    a, b = st.columns(2)
    with a:
        bd = an.summarize(df, "Branch", sort="DiscountPct")
        bd["DiscountPct"] = bd["DiscountPct"] * 100
        show(ch.bar(bd, "Branch", "DiscountPct", "Discount as % of gross, by branch", horizontal=True, fmt=".1f"))
    with b:
        ub = df.groupby("DiscountBand", observed=True)["Quantity"].mean().reset_index()
        show(ch.bar(ub, "DiscountBand", "Quantity", "Avg units per transaction by discount band", fmt=".2f"))

# --------------------------------------------------------------- Transactions
with tabs[5]:
    a, b = st.columns(2)
    with a:
        show(ch.hist(df, "NetSales", "Basket size distribution (log scale)", nbins=40, log_x=True))
    with b:
        show(ch.box(df, "Category", "NetSales", "Basket size by category (log scale)"))
    a, b = st.columns(2)
    with a:
        tb = an.summarize(df, "TicketBand", sort=None)
        show(ch.bar(tb, "TicketBand", "NetSales", "Net sales by basket-size band"))
    with b:
        show(ch.bar(tb, "TicketBand", "Transactions", "Transactions by basket-size band", fmt=",d"))
    a, b = st.columns(2)
    with a:
        qd = df.groupby("Quantity").size().reset_index(name="Transactions")
        show(ch.bar(qd, "Quantity", "Transactions", "Units per transaction", fmt=",d"))
    with b:
        show(ch.scatter(df, "Quantity", "NetSales", "Quantity vs net sales", color="Category", log=False))
    section("Largest 15 transactions")
    top = df.nlargest(15, "NetSales")[["TransactionID", "Date", "Branch", "Category", "Product", "Quantity",
                                       "UnitPrice", "DiscountPct", "NetSales"]].copy()
    top["Date"] = top["Date"].dt.strftime("%Y-%m-%d")
    top["DiscountPct"] = (top["DiscountPct"] * 100).round(1)
    table(top.rename(columns={"DiscountPct": "Discount %"}))

# -------------------------------------------------------------- Data & quality
with tabs[6]:
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Raw rows", f"{len(raw):,}", f"{raw.shape[1]} columns", "#64748B")
    kpi(c2, "Clean rows", f"{len(df_all):,}", f"{df_all.shape[1]} columns", "#0F766E")
    kpi(c3, "Rows removed", f"{len(raw) - len(df_all):,}", "duplicates / invalid", "#E11D48")
    kpi(c4, "Period", f"{df_all['Date'].min():%b %Y} – {df_all['Date'].max():%b %Y}",
        f"{df_all['Date'].nunique()} trading days", "#2563EB")
    st.write("")
    section("Cleaning & validation log")
    table(clean_log)
    section("Filtered data")
    cols_ = st.multiselect("Columns", list(df.columns), default=["TransactionID", "Date", "Branch", "Category",
                           "Subcategory", "Product", "Quantity", "UnitPrice", "DiscountPct", "NetSales"])
    table((df[cols_] if cols_ else df).assign(**({"Date": df["Date"].dt.strftime("%Y-%m-%d")} if "Date" in (cols_ or df.columns) else {})))
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="sales_filtered.csv", mime="text/csv")
    d2.download_button("⬇️ Download full cleaned data (CSV)", df_all.to_csv(index=False).encode("utf-8"),
                       file_name="Sales_clean.csv", mime="text/csv")
