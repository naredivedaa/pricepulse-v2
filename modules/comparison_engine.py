"""
PricePulse - Comparison Engine Module
Fetches multi-platform prices for a product, computes total landed costs,
and builds comparison DataFrames / Plotly charts.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional
from utils.db import get_connection
from utils.helpers import (
    PLATFORM_CONFIG, PLATFORM_ORDER, compute_total_cost,
    fmt_currency, delivery_time_tag
)


# ──────────────────────────────────────────────
# Core price fetch
# ──────────────────────────────────────────────

def get_product_comparison(product_id: str) -> pd.DataFrame:
    """
    Fetch all platform prices for a product and compute derived columns.

    Returns a DataFrame with columns:
        platform, price, mrp, discount_percent, delivery_fee, platform_fee,
        surge_fee, coupon_code, coupon_discount, delivery_time_min,
        delivery_time_max, in_stock, total_cost, effective_discount_pct,
        is_cheapest, savings_vs_max
    """
    conn = get_connection()
    try:
        sql = """
            SELECT pp.*, p.product_name, p.brand, p.image_url, p.unit, p.category
            FROM platform_prices pp
            JOIN products p ON pp.product_id = p.product_id
            WHERE pp.product_id = ?
            ORDER BY pp.price ASC
        """
        df = pd.read_sql_query(sql, conn, params=(product_id,))
    finally:
        conn.close()

    if df.empty:
        return df

    # ── Compute total landed cost ─────────────────
    df["total_cost"] = df.apply(compute_total_cost, axis=1)

    # ── Effective discount vs MRP ─────────────────
    df["effective_discount_pct"] = df.apply(
        lambda r: round(
            (r["mrp"] - r["total_cost"]) / r["mrp"] * 100, 1
        ) if r.get("mrp", 0) > 0 else 0,
        axis=1
    )

    # ── Mark cheapest in-stock option ─────────────
    in_stock = df[df["in_stock"] == 1]
    if not in_stock.empty:
        cheapest_idx = in_stock["total_cost"].idxmin()
        df["is_cheapest"] = df.index == cheapest_idx
    else:
        df["is_cheapest"] = False

    # ── Savings vs most expensive ─────────────────
    max_total = df["total_cost"].max()
    df["savings_vs_max"] = (max_total - df["total_cost"]).round(2)

    # ── Platform display info ─────────────────────
    df["platform_display"] = df["platform"].apply(
        lambda p: PLATFORM_CONFIG.get(p, {}).get("display", p.title())
    )
    df["platform_emoji"] = df["platform"].apply(
        lambda p: PLATFORM_CONFIG.get(p, {}).get("emoji", "🏪")
    )
    df["delivery_time_str"] = df.apply(
        lambda r: delivery_time_tag(
            int(r.get("delivery_time_min") or 0),
            int(r.get("delivery_time_max") or 0)
        ),
        axis=1
    )

    # Ensure platform ordering
    platform_sort = {p: i for i, p in enumerate(PLATFORM_ORDER)}
    df["_sort"] = df["platform"].map(platform_sort).fillna(99)
    df = df.sort_values("_sort").drop(columns=["_sort"])

    return df.reset_index(drop=True)


# ──────────────────────────────────────────────
# Chart builders
# ──────────────────────────────────────────────

def build_price_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """
    Stacked bar chart showing base price + delivery + fees
    for each platform, with the cheapest platform highlighted.
    """
    if df.empty:
        return go.Figure()

    platforms = []
    base_prices = []
    deliveries = []
    fees = []
    coupons = []
    colors = []
    is_cheapest_list = []

    for _, row in df.iterrows():
        if row.get("in_stock", 0) == 0:
            continue
        plat = row["platform"]
        cfg = PLATFORM_CONFIG.get(plat, {})
        platforms.append(row.get("platform_display", plat.title()))
        base_prices.append(float(row.get("price", 0)))
        deliveries.append(float(row.get("delivery_fee", 0)))
        fees.append(float(row.get("platform_fee", 0)) + float(row.get("surge_fee", 0)))
        coupons.append(-float(row.get("coupon_discount", 0)))
        colors.append(cfg.get("color", "#7C3AED"))
        is_cheapest_list.append(row.get("is_cheapest", False))

    fig = go.Figure()

    # Base price bars
    fig.add_trace(go.Bar(
        name="Base Price",
        x=platforms, y=base_prices,
        marker_color=colors,
        marker_line_color="rgba(255,255,255,0.1)",
        marker_line_width=1,
        text=[f"₹{v:.0f}" for v in base_prices],
        textposition="inside",
        textfont=dict(color="white", size=11),
    ))

    # Delivery fee
    fig.add_trace(go.Bar(
        name="Delivery Fee",
        x=platforms, y=deliveries,
        marker_color="rgba(156,163,175,0.6)",
        text=[f"₹{v:.0f}" if v > 0 else "" for v in deliveries],
        textposition="inside",
        textfont=dict(color="white", size=10),
    ))

    # Platform/surge fees
    fig.add_trace(go.Bar(
        name="Platform Fee",
        x=platforms, y=fees,
        marker_color="rgba(251,191,36,0.6)",
        text=[f"₹{v:.0f}" if v > 0 else "" for v in fees],
        textposition="inside",
        textfont=dict(color="white", size=10),
    ))

    # Coupon savings (negative)
    if any(c < 0 for c in coupons):
        fig.add_trace(go.Bar(
            name="Coupon Discount",
            x=platforms, y=coupons,
            marker_color="rgba(74,222,128,0.7)",
            text=[f"-₹{abs(v):.0f}" if v < 0 else "" for v in coupons],
            textposition="inside",
            textfont=dict(color="white", size=10),
        ))

    fig.update_layout(
        barmode="relative",
        title=dict(text="💰 Price Breakdown by Platform", font=dict(color="#E2E8F0", size=16)),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#E2E8F0"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickprefix="₹",
            tickfont=dict(size=11),
        ),
        bargap=0.25,
    )
    return fig


def build_savings_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart showing effective discount percentage per platform."""
    if df.empty:
        return go.Figure()

    in_stock_df = df[df["in_stock"] == 1]
    if in_stock_df.empty:
        return go.Figure()

    labels = in_stock_df.apply(
        lambda r: f"{r.get('platform_emoji','')} {r.get('platform_display', r['platform'])}",
        axis=1
    ).tolist()

    values = in_stock_df["effective_discount_pct"].clip(lower=0).tolist()
    colors = [PLATFORM_CONFIG.get(p, {}).get("color", "#7C3AED")
              for p in in_stock_df["platform"].tolist()]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0F0F1A", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color="white"),
    ))
    fig.update_layout(
        title=dict(text="🏷️ Effective Discount %", font=dict(color="#E2E8F0", size=14)),
        paper_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def build_delivery_time_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar showing delivery time range per platform."""
    if df.empty:
        return go.Figure()
    in_stock_df = df[df["in_stock"] == 1]
    if in_stock_df.empty:
        return go.Figure()

    platforms = in_stock_df.apply(
        lambda r: f"{r.get('platform_emoji','')} {r.get('platform_display', r['platform'])}",
        axis=1
    ).tolist()
    min_times = in_stock_df["delivery_time_min"].fillna(0).astype(int).tolist()
    max_times = in_stock_df["delivery_time_max"].fillna(0).astype(int).tolist()
    colors = [PLATFORM_CONFIG.get(p, {}).get("color", "#7C3AED")
              for p in in_stock_df["platform"].tolist()]

    fig = go.Figure()
    for i, (p, mn, mx, c) in enumerate(zip(platforms, min_times, max_times, colors)):
        fig.add_trace(go.Bar(
            name=p,
            x=[mx],
            y=[p],
            orientation="h",
            marker_color=c,
            text=f"{mn}–{mx} min",
            textposition="inside",
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text="🕐 Delivery Time Comparison", font=dict(color="#E2E8F0", size=14)),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(title="Minutes", showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        margin=dict(l=20, r=20, t=50, b=20),
        barmode="overlay",
    )
    return fig


# ──────────────────────────────────────────────
# Summary helpers
# ──────────────────────────────────────────────

def get_cheapest_option(df: pd.DataFrame) -> Optional[pd.Series]:
    """Return the row corresponding to the cheapest in-stock option."""
    in_stock = df[df["in_stock"] == 1]
    if in_stock.empty:
        return None
    idx = in_stock["total_cost"].idxmin()
    return in_stock.loc[idx]


def get_savings_summary(df: pd.DataFrame) -> dict:
    """Return a dict with cheapest / most expensive / savings info."""
    in_stock = df[df["in_stock"] == 1]
    if in_stock.empty:
        return {}
    cheapest = in_stock["total_cost"].min()
    expensive = in_stock["total_cost"].max()
    best_row = in_stock.loc[in_stock["total_cost"].idxmin()]
    return {
        "cheapest_total": cheapest,
        "most_expensive_total": expensive,
        "max_savings": round(expensive - cheapest, 2),
        "savings_pct": round((expensive - cheapest) / expensive * 100, 1) if expensive > 0 else 0,
        "best_platform": best_row.get("platform_display", ""),
        "best_platform_key": best_row.get("platform", ""),
        "product_name": best_row.get("product_name", ""),
    }
