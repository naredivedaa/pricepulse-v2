"""
PricePulse - Search Engine Module
Full-text fuzzy search with ranking, auto-complete suggestions,
and relevance scoring for grocery products.
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from typing import Optional
from utils.db import get_connection, log_search


# ──────────────────────────────────────────────
# Fuzzy match helpers
# ──────────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    """Return a 0-1 similarity score between two strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _relevance_score(query: str, product: dict) -> float:
    """
    Compute a weighted relevance score for a product given a query.
    Fields: product_name (highest), brand, category, tags.
    """
    q = query.lower().strip()
    name_sim   = _similarity(q, str(product.get("product_name", "")))
    brand_sim  = _similarity(q, str(product.get("brand", "")))
    cat_sim    = _similarity(q, str(product.get("category", "")))
    tag_sim    = _similarity(q, str(product.get("tags", "")))

    # Exact substring match bonus
    name_exact  = 0.3 if q in str(product.get("product_name", "")).lower() else 0
    brand_exact = 0.1 if q in str(product.get("brand", "")).lower() else 0

    # Popularity bonus
    pop_bonus = 0.05 if product.get("is_popular", 0) else 0

    score = (
        name_sim   * 0.50 +
        brand_sim  * 0.20 +
        cat_sim    * 0.10 +
        tag_sim    * 0.10 +
        name_exact +
        brand_exact +
        pop_bonus
    )
    return round(score, 4)


# ──────────────────────────────────────────────
# Main search function
# ──────────────────────────────────────────────

def search_products(
    query: str,
    user_id: Optional[str] = None,
    limit: int = 20,
    category_filter: Optional[str] = None,
    min_score: float = 0.1,
) -> pd.DataFrame:
    """
    Full-text + fuzzy search returning ranked products.

    Parameters
    ----------
    query          : Search term entered by the user.
    user_id        : Optional user ID for history logging.
    limit          : Maximum number of results to return.
    category_filter: Optional category to filter results.
    min_score      : Minimum relevance score (0-1) to include result.

    Returns
    -------
    DataFrame with product info + relevance_score column.
    """
    if not query or not query.strip():
        return pd.DataFrame()

    query = query.strip()
    conn = get_connection()
    try:
        # ── 1. Broad SQL pre-filter (fast) ────────
        like = f"%{query.lower()}%"
        sql = """
            SELECT p.*,
                   pp.price        AS best_price,
                   pp.platform     AS best_platform,
                   pp.mrp          AS best_mrp,
                   pp.discount_percent AS best_discount
            FROM products p
            LEFT JOIN (
                SELECT product_id,
                       MIN(price + delivery_fee + platform_fee + surge_fee - coupon_discount) AS price,
                       platform,
                       mrp,
                       discount_percent
                FROM platform_prices
                WHERE in_stock = 1
                GROUP BY product_id
            ) pp ON p.product_id = pp.product_id
            WHERE (
                LOWER(p.product_name) LIKE :like
             OR LOWER(p.brand)        LIKE :like
             OR LOWER(p.category)     LIKE :like
             OR LOWER(p.tags)         LIKE :like
            )
        """
        params = {"like": like}

        if category_filter and category_filter != "All":
            sql += " AND p.category = :cat"
            params["cat"] = category_filter

        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

    if df.empty:
        # ── Fallback: load all products and do pure fuzzy search ──
        conn2 = get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM products", conn2)
        finally:
            conn2.close()
        if df.empty:
            return df

    # ── 2. Compute relevance scores ───────────────
    df["relevance_score"] = df.apply(
        lambda row: _relevance_score(query, row.to_dict()), axis=1
    )

    # ── 3. Filter by minimum score ────────────────
    df = df[df["relevance_score"] >= min_score]

    # ── 4. Sort: exact matches first, then by score ─
    df = df.sort_values("relevance_score", ascending=False)

    # ── 5. Apply limit ────────────────────────────
    df = df.head(limit).reset_index(drop=True)

    # ── 6. Log the search ─────────────────────────
    log_search(user_id, query, len(df))

    return df


# ──────────────────────────────────────────────
# Auto-complete / suggestions
# ──────────────────────────────────────────────

def get_suggestions(partial: str, limit: int = 8) -> list[str]:
    """
    Return product name suggestions for a partial query.
    Used for real-time search-as-you-type dropdown.
    """
    if not partial or len(partial) < 2:
        return []

    conn = get_connection()
    try:
        like = f"%{partial.lower()}%"
        rows = conn.execute(
            """SELECT DISTINCT product_name FROM products
               WHERE LOWER(product_name) LIKE ?
               ORDER BY is_popular DESC, product_name ASC
               LIMIT ?""",
            (like, limit)
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Category listing
# ──────────────────────────────────────────────

def get_all_categories() -> list[str]:
    """Return sorted list of all product categories."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()
        return ["All"] + [r[0] for r in rows if r[0]]
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Featured / Popular
# ──────────────────────────────────────────────

def get_popular_products(limit: int = 8) -> pd.DataFrame:
    """Fetch popular products with best platform price."""
    conn = get_connection()
    try:
        sql = """
            SELECT p.*,
                   MIN(pp.price + pp.delivery_fee + pp.platform_fee
                       + pp.surge_fee - pp.coupon_discount) AS best_total,
                   bp.platform AS best_platform,
                   bp.price    AS best_price,
                   bp.mrp      AS mrp
            FROM products p
            LEFT JOIN platform_prices pp ON p.product_id = pp.product_id AND pp.in_stock = 1
            LEFT JOIN (
                SELECT product_id, platform, price, mrp
                FROM platform_prices
                WHERE (product_id, price) IN (
                    SELECT product_id, MIN(price)
                    FROM platform_prices WHERE in_stock = 1
                    GROUP BY product_id
                )
            ) bp ON p.product_id = bp.product_id
            WHERE p.is_popular = 1
            GROUP BY p.product_id
            LIMIT ?
        """
        return pd.read_sql_query(sql, conn, params=(limit,))
    finally:
        conn.close()
