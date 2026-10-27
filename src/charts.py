"""Plotly figure builders with one consistent visual style."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

SEQ = ["#0F766E", "#2563EB", "#F59E0B", "#E11D48", "#7C3AED", "#06B6D4", "#84CC16", "#EC4899", "#64748B"]
YEAR_COLORS = {"2023": "#94A3B8", "2024": "#2563EB", "2025": "#0F766E"}
INK = "#1F2937"
TEAL_SCALE = [[0, "#E6FFFA"], [0.5, "#2DD4BF"], [1, "#0F766E"]]
LABELS = {"NetSales": "Net sales (PKR)", "GrossSales": "Gross sales (PKR)", "DiscountAmt": "Discount (PKR)",
          "AvgTicket": "Avg basket (PKR)", "Transactions": "Transactions", "Units": "Units sold",
          "DiscountPct": "Discount % of gross", "YearMonth": "Month", "UnitPrice": "Unit price (PKR)"}


def style(fig, title=None, height=380, legend=True):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=56 if title else 24, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=12, color=INK), showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=""))
    if title:
        fig.update_layout(title=dict(text=f"<b>{title}</b>", x=0, xanchor="left", font=dict(size=15)))
    return fig


def bar(data: pd.DataFrame, x: str, y: str, title: str, horizontal=False, color=None, height=360,
        fmt=".3s", stack=False):
    """Ranked bar chart. fmt is a d3 format for the value labels (default compact: 1.5M)."""
    if horizontal:
        fig = px.bar(data, y=x, x=y, orientation="h", color=color, color_discrete_sequence=SEQ, labels=LABELS)
        fig.update_yaxes(autorange="reversed", title=None)
        fig.update_xaxes(title=None)
    else:
        fig = px.bar(data, x=x, y=y, color=color, color_discrete_sequence=SEQ, labels=LABELS)
        fig.update_xaxes(title=None, type="category")
        fig.update_yaxes(title=None)
    fig.update_layout(barmode="relative" if stack else "group")
    if color is None:
        fig.update_traces(marker_color=SEQ[0], texttemplate=f"%{{{'x' if horizontal else 'y'}:{fmt}}}",
                          textposition="outside", cliponaxis=False)
    return style(fig, title, height, legend=color is not None)


def donut(data: pd.DataFrame, names: str, values: str, title: str, height=340):
    fig = px.pie(data, names=names, values=values, hole=0.6, color_discrete_sequence=SEQ)
    fig.update_traces(textinfo="percent+label", sort=False)
    return style(fig, title, height, legend=False)


def treemap(data: pd.DataFrame, path: list[str], values: str, title: str, color: str | None = None, height=450):
    fig = px.treemap(data, path=path, values=values, color=color or values, color_continuous_scale=TEAL_SCALE)
    fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.3s}")
    fig.update_layout(coloraxis_showscale=False)
    return style(fig, title, height, legend=False)


def monthly_bars(m: pd.DataFrame, title: str, height=380):
    fig = px.bar(m, x="YearMonth", y="NetSales", labels=LABELS)
    fig.update_traces(marker_color="#99F6E4", name="Net sales", showlegend=True)
    fig.add_trace(go.Scatter(x=m["YearMonth"], y=m["MA3"], mode="lines", name="3-month average",
                             line=dict(color="#0F766E", width=3)))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    return style(fig, title, height)


def year_lines(m: pd.DataFrame, title: str, height=380):
    fig = px.line(m, x="Month", y="NetSales", color="Year", markers=True, color_discrete_map=YEAR_COLORS,
                  category_orders={"Month": ["January", "February", "March", "April", "May", "June", "July",
                                             "August", "September", "October", "November", "December"]},
                  labels=LABELS)
    fig.update_xaxes(title=None, tickangle=-35)
    fig.update_yaxes(title=None)
    return style(fig, title, height)


def heatmap(p: pd.DataFrame, title: str, fmt=".3s", scale=TEAL_SCALE, height=400):
    fig = px.imshow(p, text_auto=fmt, aspect="auto", color_continuous_scale=scale)
    fig.update_xaxes(title=p.columns.name)
    fig.update_yaxes(title=p.index.name)
    fig.update_layout(coloraxis_showscale=False)
    return style(fig, title, height, legend=False)


def pareto(p: pd.DataFrame, by: str, title: str, height=420):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=p[by], y=p["NetSales"], name="Net sales", marker_color=SEQ[0]))
    fig.add_trace(go.Scatter(x=p[by], y=p["CumShare"], name="Cumulative share", yaxis="y2", mode="lines+markers",
                             line=dict(color="#F59E0B", width=3)))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0, 1.05], showgrid=False))
    fig.update_xaxes(tickangle=-45)
    return style(fig, title, height)


def hist(df: pd.DataFrame, x: str, title: str, nbins=30, log_x=False, color=None, height=340):
    fig = px.histogram(df, x=x, nbins=nbins, log_x=log_x, color=color, color_discrete_sequence=SEQ,
                       barmode="overlay", opacity=0.8, labels=LABELS)
    fig.update_yaxes(title="Transactions")
    return style(fig, title, height, legend=color is not None)


def box(df: pd.DataFrame, x: str, y: str, title: str, log_y=True, height=400):
    fig = px.box(df, x=x, y=y, log_y=log_y, color=x, color_discrete_sequence=SEQ, labels=LABELS)
    fig.update_xaxes(title=None, tickangle=-30)
    return style(fig, title, height, legend=False)


def scatter(df: pd.DataFrame, x: str, y: str, title: str, color=None, height=380, log=False):
    fig = px.scatter(df, x=x, y=y, color=color, opacity=0.6, log_x=log, log_y=log, color_discrete_sequence=SEQ,
                     hover_data=["Product", "Branch"], labels=LABELS)
    return style(fig, title, height, legend=color is not None)
