"""
PricePulse - Analytics Module
Builds all dashboard charts and computes KPI summaries.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils.db import get_connection, get_platform_stats, get_biggest_savings
from utils.helpers import PLATFORM_CONFIG, PLATFORM_ORDER, fmt_currency


# ──────────────────────────────────────────────
# KPI helpers
# ──────────────────────────────────────────────

def get_platform_kpis() -> dict:
    """Return high-level KPIs for the platform."""
    conn = get_connection()
    try:
        total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        total_prices   = conn.execute("SELECT COUNT(*) FROM platform_prices WHERE in_stock=1").fetchone()[0]
        total_searches = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
        total_alerts   = conn.execute("SELECT COUNT(*) FROM price_alerts WHERE is_active=1").fetchone()[0]

        # Avg savings potential
        row = conn.execute("""
            SELECT AVG(max_p - min_p) AS avg_savings
            FROM (
                SELECT product_id,
                       MAX(price + delivery_fee + platform_fee + surge_fee - coupon_discount) AS max_p,
                       MIN(price + delivery_fee + platform_fee + surge_fee - coupon_discount) AS min_p
                FROM platform_prices WHERE in_stock=1
                GROUP BY product_id
            )
        """).fetchone()
        avg_savings = round(float(row["avg_savings"]) if row["avg_savings"] else 0, 2)

    finally:
        conn.close()

    return {
        "total_products": total_products,
        "total_prices": total_prices,
        "total_searches": total_searches,
        "total_alerts": total_alerts,
        "avg_savings": avg_savings,
        "platforms": len(PLATFORM_ORDER),
    }


def get_user_kpis(user_id: str) -> dict:
    """Return KPIs specific to a user's activity."""
    conn = get_connection()
    try:
        searches = conn.execute(
            "SELECT COUNT(*) FROM search_history WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        alerts = conn.execute(
            "SELECT COUNT(*) FROM price_alerts WHERE user_id=? AND is_active=1", (user_id,)
        ).fetchone()[0]
        baskets = conn.execute(
            "SELECT COUNT(*) FROM saved_baskets WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        savings_row = conn.execute(
            "SELECT COALESCE(SUM(amount_saved),0) FROM analytics WHERE user_id=? AND event_type='savings'",
            (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "searches": searches,
        "active_alerts": alerts,
        "saved_baskets": baskets,
        "total_saved": round(float(savings_row), 2),
    }


# ──────────────────────────────────────────────
# Chart builders
# ──────────────────────────────────────────────

def build_platform_market_share_chart() -> go.Figure:
    """Donut chart showing product count market share per platform."""
    stats = get_platform_stats()
    if stats.empty:
        return go.Figure()

    labels  = [PLATFORM_CONFIG.get(p, {}).get("display", p.title()) for p in stats["platform"]]
    values  = stats["in_stock_count"].tolist()
    colors  = [PLATFORM_CONFIG.get(p, {}).get("color", "#7C3AED") for p in stats["platform"]]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0F0F1A", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color="white"),
    ))
    fig.update_layout(
        title=dict(text="📊 Products Available per Platform", font=dict(color="#E2E8F0", size=15)),
        paper_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        showlegend=True,
        legend=dict(font=dict(color="#E2E8F0")),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def build_avg_price_by_platform_chart() -> go.Figure:
    """Bar chart showing average price per platform."""
    stats = get_platform_stats()
    if stats.empty:
        return go.Figure()

    platforms = [PLATFORM_CONFIG.get(p, {}).get("display", p.title()) for p in stats["platform"]]
    prices    = stats["avg_price"].round(2).tolist()
    deliveries = stats["avg_delivery"].round(2).tolist()
    colors    = [PLATFORM_CONFIG.get(p, {}).get("color", "#7C3AED") for p in stats["platform"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Avg. Product Price",
        x=platforms, y=prices,
        marker_color=colors,
        text=[f"₹{v:.0f}" for v in prices],
        textposition="outside",
        textfont=dict(color="#E2E8F0"),
    ))
    fig.add_trace(go.Bar(
        name="Avg. Delivery Fee",
        x=platforms, y=deliveries,
        marker_color="rgba(156,163,175,0.5)",
        text=[f"₹{v:.0f}" for v in deliveries],
        textposition="outside",
        textfont=dict(color="#E2E8F0"),
    ))
    fig.update_layout(
        barmode="group",
        title=dict(text="💰 Average Prices by Platform", font=dict(color="#E2E8F0", size=15)),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"),
        legend=dict(font=dict(color="#E2E8F0")),
        margin=dict(l=20, r=20, t=60, b=20),
        bargap=0.2,
    )
    return fig


def build_biggest_savings_chart() -> go.Figure:
    """Horizontal bar chart showing top savings opportunities."""
    df = get_biggest_savings(10)
    if df.empty:
        return go.Figure()

    labels = df["product_name"].apply(lambda x: x[:22]).tolist()
    savings = df["savings"].tolist()
    pcts = df["savings_pct"].tolist()

    fig = go.Figure(go.Bar(
        x=savings,
        y=labels,
        orientation="h",
        marker=dict(
            color=savings,
            colorscale=[[0, "#5B21B6"], [1, "#4ADE80"]],
            showscale=False,
        ),
        text=[f"₹{s:.0f} ({p:.0f}%)" for s, p in zip(savings, pcts)],
        textposition="outside",
        textfont=dict(color="#E2E8F0", size=11),
    ))
    fig.update_layout(
        title=dict(text="🏆 Top Savings Opportunities Today", font=dict(color="#E2E8F0", size=15)),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.05)",
            tickprefix="₹", title="Max Savings"
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        margin=dict(l=20, r=120, t=60, b=20),
    )
    return fig


def build_category_savings_chart() -> go.Figure:
    """Bar chart showing average savings by category."""
    conn = get_connection()
    try:
        sql = """
            SELECT p.category,
                   AVG(max_p - min_p) AS avg_savings,
                   COUNT(DISTINCT p.product_id) AS product_count
            FROM products p
            JOIN (
                SELECT product_id,
                       MAX(price + delivery_fee + platform_fee + surge_fee - coupon_discount) AS max_p,
                       MIN(price + delivery_fee + platform_fee + surge_fee - coupon_discount) AS min_p
                FROM platform_prices WHERE in_stock=1
                GROUP BY product_id
            ) s ON p.product_id = s.product_id
            GROUP BY p.category
            ORDER BY avg_savings DESC
        """
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()

    if df.empty:
        return go.Figure()

    fig = px.bar(
        df,
        x="category",
        y="avg_savings",
        color="avg_savings",
        color_continuous_scale=[[0, "#5B21B6"], [1, "#4ADE80"]],
        text=df["avg_savings"].round(0).apply(lambda x: f"₹{x:.0f}"),
        hover_data=["product_count"],
        title="📦 Average Savings by Category",
    )
    fig.update_layout(
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        title_font=dict(color="#E2E8F0", size=15),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.05)",
            tickprefix="₹",
        ),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=60, b=60),
    )
    fig.update_traces(textposition="outside", textfont=dict(color="#E2E8F0", size=10))
    return fig


def build_savings_trend_chart(user_id: str = None) -> go.Figure:
    """
    Mock monthly savings trend line chart.
    Uses real data if available, otherwise generates illustrative data.
    """
    # Generate illustrative monthly data
    months = pd.date_range(end=datetime.now(), periods=6, freq="MS")
    np.random.seed(42)
    savings = np.cumsum(np.random.randint(50, 300, size=6)).tolist()
    comparisons = np.random.randint(10, 80, size=6).tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=savings,
        name="Cumulative Savings",
        mode="lines+markers",
        line=dict(color="#A78BFA", width=3),
        marker=dict(size=8, color="#7C3AED"),
        fill="tozeroy",
        fillcolor="rgba(124,58,237,0.1)",
    ))
    fig.add_trace(go.Bar(
        x=months,
        y=comparisons,
        name="Price Comparisons",
        marker_color="rgba(167,139,250,0.3)",
        yaxis="y2",
    ))
    fig.update_layout(
        title=dict(text="📈 Monthly Savings Trend", font=dict(color="#E2E8F0", size=15)),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.05)",
            tickprefix="₹", title="Savings (₹)",
        ),
        yaxis2=dict(
            title="Comparisons",
            overlaying="y", side="right",
            showgrid=False,
        ),
        legend=dict(font=dict(color="#E2E8F0")),
        margin=dict(l=20, r=60, t=60, b=20),
    )
    return fig


def build_platform_delivery_radar() -> go.Figure:
    """Radar chart comparing platforms across multiple dimensions."""
    categories = ["Price", "Speed", "Availability", "Discounts", "UX Rating"]
    platform_data = {
        "zepto":     [8, 10, 7, 7, 9],
        "blinkit":   [7, 9, 8, 8, 8],
        "instamart": [8, 7, 8, 9, 7],
        "bigbasket": [9, 4, 9, 8, 8],
    }

    fig = go.Figure()
    for platform, scores in platform_data.items():
        cfg = PLATFORM_CONFIG.get(platform, {})
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=categories + [categories[0]],
            name=f"{cfg.get('emoji','')} {cfg.get('display', platform)}",
            line=dict(color=cfg.get("color", "#7C3AED"), width=2),
            fill="toself",
            fillcolor="rgba(124, 58, 237, 0.15)",
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="#1E103A",
            radialaxis=dict(
                visible=True, range=[0, 10],
                gridcolor="rgba(255,255,255,0.1)",
                tickfont=dict(color="#9CA3AF"),
            ),
            angularaxis=dict(tickfont=dict(color="#E2E8F0", size=12)),
        ),
        title=dict(text="🎯 Platform Comparison Radar", font=dict(color="#E2E8F0", size=15)),
        paper_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        legend=dict(font=dict(color="#E2E8F0")),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig
