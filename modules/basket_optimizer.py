"""
PricePulse - Basket Optimizer Module
Computes per-platform basket totals and recommends the optimal
buy strategy: single-platform vs split-basket purchasing.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from itertools import combinations
from typing import Optional
from utils.db import get_connection
from utils.helpers import PLATFORM_CONFIG, PLATFORM_ORDER, compute_total_cost, fmt_currency


# ──────────────────────────────────────────────
# Basket computation
# ──────────────────────────────────────────────

def compute_basket_totals(basket_items: list[dict]) -> dict:
    """
    Given a list of basket items (each a dict with product_id, quantity),
    compute the total cost for each platform.

    Parameters
    ----------
    basket_items : [{"product_id": "P001", "quantity": 2, "product_name": "..."}, ...]

    Returns
    -------
    {
        "platform_totals": {"zepto": 123.0, "blinkit": 130.0, ...},
        "item_breakdown": pd.DataFrame,
        "missing_items": {platform: [product_names]},
    }
    """
    if not basket_items:
        return {"platform_totals": {}, "item_breakdown": pd.DataFrame(), "missing_items": {}}

    product_ids = [item["product_id"] for item in basket_items]
    quantities  = {item["product_id"]: item.get("quantity", 1) for item in basket_items}

    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(product_ids))
        sql = f"""
            SELECT pp.*, p.product_name, p.brand, p.unit
            FROM platform_prices pp
            JOIN products p ON pp.product_id = p.product_id
            WHERE pp.product_id IN ({placeholders})
        """
        df = pd.read_sql_query(sql, conn, params=product_ids)
    finally:
        conn.close()

    if df.empty:
        return {"platform_totals": {}, "item_breakdown": df, "missing_items": {}}

    # Compute per-item total cost
    df["unit_cost"] = df.apply(compute_total_cost, axis=1)
    df["quantity"]  = df["product_id"].map(quantities).fillna(1)
    df["line_cost"] = df["unit_cost"] * df["quantity"]

    # Platform totals (items in stock only)
    platform_totals = {}
    missing_items   = {}

    for platform in PLATFORM_ORDER:
        plat_df = df[df["platform"] == platform]
        in_stock_df = plat_df[plat_df["in_stock"] == 1]

        # Items not available on this platform
        available_ids = set(in_stock_df["product_id"].tolist())
        missing = [
            item["product_name"]
            for item in basket_items
            if item["product_id"] not in available_ids
        ]
        missing_items[platform] = missing

        # Sum only available items
        platform_totals[platform] = round(in_stock_df["line_cost"].sum(), 2)

    # Build item breakdown DataFrame
    breakdown_rows = []
    for item in basket_items:
        pid = item["product_id"]
        row_data = {"product_name": item.get("product_name", pid), "quantity": quantities[pid]}
        for platform in PLATFORM_ORDER:
            plat_row = df[(df["product_id"] == pid) & (df["platform"] == platform)]
            if plat_row.empty or plat_row.iloc[0]["in_stock"] == 0:
                row_data[platform] = None  # Not available
            else:
                row_data[platform] = round(plat_row.iloc[0]["line_cost"], 2)
        breakdown_rows.append(row_data)

    breakdown_df = pd.DataFrame(breakdown_rows)

    return {
        "platform_totals": platform_totals,
        "item_breakdown": breakdown_df,
        "missing_items": missing_items,
    }


# ──────────────────────────────────────────────
# Smart Basket Optimizer
# ──────────────────────────────────────────────

def optimize_basket(basket_items: list[dict]) -> dict:
    """
    Find the cheapest way to buy the full basket:
    - Option A: Buy everything from the single cheapest platform
    - Option B: Split items across platforms for lowest total

    Returns a rich dict with recommendations and savings breakdown.
    """
    result = compute_basket_totals(basket_items)
    platform_totals = result["platform_totals"]
    breakdown_df    = result["item_breakdown"]

    if not platform_totals:
        return {"strategy": "no_data", "message": "No price data found for basket items."}

    # ── Option A: Single platform ──────────────────
    valid_totals = {k: v for k, v in platform_totals.items() if v > 0}
    if not valid_totals:
        return {"strategy": "no_data", "message": "No in-stock items found."}

    best_single_platform = min(valid_totals, key=valid_totals.get)
    best_single_cost = valid_totals[best_single_platform]

    # ── Option B: Split basket ─────────────────────
    split_cost, split_plan = _compute_split_basket(breakdown_df, basket_items)

    # ── Determine best strategy ────────────────────
    # Add small threshold: split only if saves > ₹5
    if split_cost < best_single_cost - 5:
        strategy = "split"
        recommended_cost = split_cost
    else:
        strategy = "single"
        recommended_cost = best_single_cost

    return {
        "strategy": strategy,
        "single_platform": best_single_platform,
        "single_platform_display": PLATFORM_CONFIG.get(best_single_platform, {}).get("display", ""),
        "single_cost": best_single_cost,
        "split_cost": split_cost,
        "split_plan": split_plan,
        "recommended_cost": recommended_cost,
        "savings_vs_expensive": max(valid_totals.values()) - recommended_cost,
        "savings_split_vs_single": max(0, best_single_cost - split_cost),
        "platform_totals": platform_totals,
        "item_breakdown": breakdown_df,
        "missing_items": result["missing_items"],
    }


def _compute_split_basket(breakdown_df: pd.DataFrame, basket_items: list[dict]) -> tuple[float, list]:
    """
    Greedy item-by-item platform assignment: for each product pick the
    cheapest platform it's available on.

    Returns (total_split_cost, split_plan_list)
    split_plan_list: [{"product_name": ..., "platform": ..., "cost": ...}, ...]
    """
    split_plan = []
    total = 0.0

    for _, row in breakdown_df.iterrows():
        best_platform = None
        best_cost = float("inf")
        for platform in PLATFORM_ORDER:
            cost = row.get(platform)
            if cost is not None and cost < best_cost:
                best_cost = cost
                best_platform = platform

        if best_platform:
            split_plan.append({
                "product_name": row["product_name"],
                "platform": best_platform,
                "platform_display": PLATFORM_CONFIG.get(best_platform, {}).get("display", ""),
                "cost": round(best_cost, 2),
                "quantity": int(row.get("quantity", 1)),
            })
            total += best_cost

    return round(total, 2), split_plan


# ──────────────────────────────────────────────
# Charts
# ──────────────────────────────────────────────

def build_basket_comparison_chart(platform_totals: dict) -> go.Figure:
    """Grouped bar chart comparing basket totals per platform."""
    if not platform_totals:
        return go.Figure()

    platforms = []
    totals = []
    colors = []
    min_cost = min(v for v in platform_totals.values() if v > 0)

    for plat in PLATFORM_ORDER:
        total = platform_totals.get(plat, 0)
        if total == 0:
            continue
        cfg = PLATFORM_CONFIG.get(plat, {})
        platforms.append(f"{cfg.get('emoji','')} {cfg.get('display', plat)}")
        totals.append(total)
        colors.append("#4ADE80" if total == min_cost else cfg.get("color", "#7C3AED"))

    fig = go.Figure(go.Bar(
        x=platforms,
        y=totals,
        marker_color=colors,
        text=[f"₹{t:.0f}" for t in totals],
        textposition="outside",
        textfont=dict(color="#E2E8F0", size=13),
        marker_line_color="rgba(255,255,255,0.1)",
        marker_line_width=1,
    ))

    # Mark cheapest
    min_idx = totals.index(min(totals)) if totals else None
    if min_idx is not None:
        fig.add_annotation(
            x=platforms[min_idx],
            y=totals[min_idx],
            text="✅ CHEAPEST",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#4ADE80",
            font=dict(color="#4ADE80", size=12),
            yshift=20,
        )

    fig.update_layout(
        title=dict(text="🛒 Basket Total by Platform", font=dict(color="#E2E8F0", size=16)),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(showgrid=False, tickfont=dict(size=12)),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickprefix="₹",
            tickfont=dict(size=11),
        ),
        margin=dict(l=20, r=20, t=70, b=20),
        bargap=0.3,
    )
    return fig


def build_split_savings_chart(opt: dict) -> go.Figure:
    """Bar chart comparing single-platform cost vs. split-basket cost."""
    if "single_cost" not in opt:
        return go.Figure()

    labels = ["Best Single Platform", "Split Basket (Optimized)"]
    values = [opt["single_cost"], opt["split_cost"]]
    colors = ["#7C3AED", "#4ADE80"]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"₹{v:.0f}" for v in values],
        textposition="outside",
        textfont=dict(color="#E2E8F0", size=14, weight=700 ),
    ))

    fig.update_layout(
        title=dict(
            text=f"💡 Save ₹{opt.get('savings_split_vs_single', 0):.0f} by splitting the basket",
            font=dict(color="#A78BFA", size=15)
        ),
        paper_bgcolor="#0F0F1A",
        plot_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(showgrid=False),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickprefix="₹",
        ),
        margin=dict(l=20, r=20, t=70, b=20),
        bargap=0.4,
    )
    return fig


def build_item_heatmap(breakdown_df: pd.DataFrame) -> go.Figure:
    """Heatmap of per-item costs across platforms."""
    if breakdown_df.empty:
        return go.Figure()

    platform_cols = [p for p in PLATFORM_ORDER if p in breakdown_df.columns]
    if not platform_cols:
        return go.Figure()

    z_data = []
    y_labels = []
    for _, row in breakdown_df.iterrows():
        vals = [row.get(p) for p in platform_cols]
        z_data.append(vals)
        y_labels.append(str(row.get("product_name", ""))[:25])

    x_labels = [PLATFORM_CONFIG.get(p, {}).get("display", p) for p in platform_cols]

    fig = go.Figure(go.Heatmap(
        z=z_data,
        x=x_labels,
        y=y_labels,
        colorscale=[
            [0.0, "#1a472a"],   # Cheapest = green
            [0.5, "#5B21B6"],   # Mid = purple
            [1.0, "#991B1B"],   # Expensive = red
        ],
        text=[[f"₹{v:.0f}" if v else "N/A" for v in row] for row in z_data],
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title="₹ Cost", tickprefix="₹", tickfont=dict(color="#E2E8F0")),
    ))

    fig.update_layout(
        title=dict(text="📊 Item-Platform Cost Matrix", font=dict(color="#E2E8F0", size=14)),
        paper_bgcolor="#0F0F1A",
        font=dict(color="#E2E8F0"),
        xaxis=dict(tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig
