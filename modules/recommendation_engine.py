"""
PricePulse - Recommendation Engine Module
Content-based product recommendations using TF-IDF vectorisation
and cosine similarity. Also provides "Frequently Bought Together"
and "Best Deals" suggestions.
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.db import get_connection
from utils.helpers import PLATFORM_CONFIG, PLATFORM_ORDER


# ──────────────────────────────────────────────
# Lazy-loaded recommendation model
# ──────────────────────────────────────────────
_MODEL_CACHE = {}


def _build_model() -> dict:
    """Build and cache the TF-IDF similarity model."""
    if _MODEL_CACHE:
        return _MODEL_CACHE

    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT product_id, product_name, brand, category, subcategory, tags FROM products",
            conn
        )
    finally:
        conn.close()

    if df.empty:
        return {}

    # Combine text features
    df["text_features"] = (
        df["product_name"].fillna("") + " " +
        df["brand"].fillna("") + " " +
        df["category"].fillna("") + " " +
        df["subcategory"].fillna("") + " " +
        df["tags"].fillna("")
    ).str.lower()

    # TF-IDF vectorisation
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
    )
    tfidf_matrix = vectorizer.fit_transform(df["text_features"])

    # Cosine similarity matrix
    sim_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    _MODEL_CACHE.update({
        "df": df.reset_index(drop=True),
        "sim_matrix": sim_matrix,
        "product_ids": df["product_id"].tolist(),
    })
    return _MODEL_CACHE


def get_similar_products(product_id: str, top_n: int = 6) -> pd.DataFrame:
    """
    Return top-N similar products based on content similarity.

    Parameters
    ----------
    product_id : ID of the reference product.
    top_n      : Number of recommendations to return.

    Returns
    -------
    DataFrame with product details and similarity_score column.
    """
    model = _build_model()
    if not model:
        return pd.DataFrame()

    product_ids = model["product_ids"]
    if product_id not in product_ids:
        return pd.DataFrame()

    idx = product_ids.index(product_id)
    sim_scores = list(enumerate(model["sim_matrix"][idx]))

    # Sort by similarity, exclude self
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = [(i, s) for i, s in sim_scores if i != idx][:top_n]

    df = model["df"]
    rec_df = df.iloc[[i for i, _ in sim_scores]].copy()
    rec_df["similarity_score"] = [round(s, 3) for _, s in sim_scores]

    # Enrich with best price
    rec_df = _enrich_with_prices(rec_df)
    return rec_df.reset_index(drop=True)


def get_category_recommendations(category: str, exclude_id: str = None,
                                  top_n: int = 6) -> pd.DataFrame:
    """Return top products in the same category, sorted by savings potential."""
    conn = get_connection()
    try:
        sql = """
            SELECT p.*,
                   MIN(pp.price + pp.delivery_fee + pp.platform_fee
                       + pp.surge_fee - pp.coupon_discount) AS best_total,
                   MAX(pp.price)                            AS max_price,
                   MIN(pp.price)                            AS min_price
            FROM products p
            JOIN platform_prices pp ON p.product_id = pp.product_id AND pp.in_stock = 1
            WHERE p.category = ?
        """
        params = [category]
        if exclude_id:
            sql += " AND p.product_id != ?"
            params.append(exclude_id)
        sql += " GROUP BY p.product_id ORDER BY (MAX(pp.price)-MIN(pp.price)) DESC LIMIT ?"
        params.append(top_n)

        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()
    return df


def get_best_deals(limit: int = 10) -> pd.DataFrame:
    """Return products sorted by highest savings percentage across platforms."""
    conn = get_connection()
    try:
        sql = """
            SELECT p.product_id, p.product_name, p.brand, p.category, p.image_url,
                   MAX(pp.price) AS max_price,
                   MIN(pp.price + pp.delivery_fee + pp.platform_fee
                       + pp.surge_fee - pp.coupon_discount) AS best_total,
                   MAX(pp.mrp)   AS mrp,
                   bp.platform   AS best_platform,
                   bp.price      AS cheapest_price
            FROM products p
            JOIN platform_prices pp ON p.product_id = pp.product_id AND pp.in_stock = 1
            JOIN (
                SELECT product_id, platform, price
                FROM platform_prices
                WHERE (product_id, price + delivery_fee + platform_fee + surge_fee - coupon_discount)
                    IN (
                        SELECT product_id,
                               MIN(price + delivery_fee + platform_fee + surge_fee - coupon_discount)
                        FROM platform_prices WHERE in_stock = 1
                        GROUP BY product_id
                    )
            ) bp ON p.product_id = bp.product_id
            GROUP BY p.product_id
            HAVING COUNT(DISTINCT pp.platform) >= 2
               AND (MAX(pp.price) - best_total) > 5
            ORDER BY (MAX(pp.price) - best_total) / MAX(pp.price) DESC
            LIMIT ?
        """
        df = pd.read_sql_query(sql, conn, params=(limit,))
    finally:
        conn.close()
    if not df.empty:
        df["savings_amount"] = (df["max_price"] - df["best_total"]).round(2)
        df["savings_pct"] = (df["savings_amount"] / df["max_price"] * 100).round(1)
        df["platform_display"] = df["best_platform"].apply(
            lambda p: PLATFORM_CONFIG.get(p, {}).get("display", p.title())
        )
    return df


# ──────────────────────────────────────────────
# AI-style shopping list builder (mock)
# ──────────────────────────────────────────────

RECIPE_TEMPLATES = {
    "pasta": {
        "ingredients": ["Penne Pasta", "Tomato Sauce", "Cheese", "Olive Oil", "Garlic"],
        "keywords": ["pasta", "penne", "spaghetti", "macaroni"],
    },
    "sandwich": {
        "ingredients": ["Bread", "Butter", "Cheese", "Tomato Ketchup"],
        "keywords": ["sandwich", "toast", "bread"],
    },
    "tea": {
        "ingredients": ["Tea", "Milk", "Sugar"],
        "keywords": ["tea", "chai", "morning"],
    },
    "dal": {
        "ingredients": ["Toor Dal", "Tata Salt", "Fortune Oil", "Atta"],
        "keywords": ["dal", "daal", "lentil"],
    },
    "noodles": {
        "ingredients": ["Maggi Noodles", "Ching's Hakka Noodles", "Lay's Chips"],
        "keywords": ["noodles", "maggi", "instant", "snack"],
    },
}


def parse_shopping_query(query: str) -> dict:
    """
    Mock AI parser: detect recipe intent and return a shopping list.

    Returns
    -------
    {
        "intent": "recipe" | "budget" | "generic",
        "recipe": str,
        "shopping_list": [product_names],
        "products": pd.DataFrame,
        "estimated_cost": float,
        "cheapest_platform": str,
    }
    """
    query_lower = query.lower()

    # ── Detect recipe intent ──────────────────────
    matched_recipe = None
    for recipe, data in RECIPE_TEMPLATES.items():
        if any(kw in query_lower for kw in data["keywords"]):
            matched_recipe = recipe
            break

    shopping_list = []
    if matched_recipe:
        shopping_list = RECIPE_TEMPLATES[matched_recipe]["ingredients"]

    # ── Budget detection ──────────────────────────
    budget = None
    import re
    budget_match = re.search(r"(?:under|below|within|₹|rs\.?)\s*(\d+)", query_lower)
    if budget_match:
        budget = float(budget_match.group(1))

    # ── Search for matching products ──────────────
    if shopping_list:
        products = _search_shopping_list(shopping_list)
    else:
        # Generic search
        conn = get_connection()
        try:
            words = query_lower.split()
            results = []
            for word in words:
                if len(word) > 3:
                    like = f"%{word}%"
                    rows = pd.read_sql_query(
                        "SELECT * FROM products WHERE LOWER(product_name) LIKE ? LIMIT 3",
                        conn, params=(like,)
                    )
                    results.append(rows)
            products = pd.concat(results).drop_duplicates("product_id") if results else pd.DataFrame()
        finally:
            conn.close()

    # ── Compute costs ─────────────────────────────
    estimated_cost = 0.0
    cheapest_platform = "zepto"

    if not products.empty:
        conn = get_connection()
        try:
            ids = products["product_id"].tolist()
            placeholders = ",".join("?" * len(ids))
            price_df = pd.read_sql_query(
                f"SELECT * FROM platform_prices WHERE product_id IN ({placeholders}) AND in_stock=1",
                conn, params=ids
            )
        finally:
            conn.close()

        if not price_df.empty:
            platform_costs = {}
            for platform in PLATFORM_ORDER:
                plat_df = price_df[price_df["platform"] == platform]
                if not plat_df.empty:
                    from utils.helpers import compute_total_cost
                    plat_df = plat_df.copy()
                    plat_df["total_cost"] = plat_df.apply(compute_total_cost, axis=1)
                    min_costs = plat_df.groupby("product_id")["total_cost"].min()
                    platform_costs[platform] = round(min_costs.sum(), 2)

            if platform_costs:
                cheapest_platform = min(platform_costs, key=platform_costs.get)
                estimated_cost = platform_costs[cheapest_platform]

                # Apply budget filter
                if budget and estimated_cost > budget:
                    # Trim expensive items
                    products = products.head(max(1, len(products) - 2))
                    estimated_cost = round(estimated_cost * 0.75, 2)

    return {
        "intent": "recipe" if matched_recipe else "generic",
        "recipe": matched_recipe or "custom list",
        "shopping_list": shopping_list or products.get("product_name", pd.Series()).tolist(),
        "products": products,
        "estimated_cost": estimated_cost,
        "cheapest_platform": cheapest_platform,
        "cheapest_platform_display": PLATFORM_CONFIG.get(cheapest_platform, {}).get("display", ""),
        "budget": budget,
    }


# ──────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────

def _search_shopping_list(ingredient_names: list[str]) -> pd.DataFrame:
    """Search for products matching ingredient names."""
    conn = get_connection()
    try:
        results = []
        for name in ingredient_names:
            like = f"%{name.lower()}%"
            row = pd.read_sql_query(
                "SELECT * FROM products WHERE LOWER(product_name) LIKE ? LIMIT 1",
                conn, params=(like,)
            )
            if not row.empty:
                results.append(row)
        return pd.concat(results).drop_duplicates("product_id") if results else pd.DataFrame()
    finally:
        conn.close()


def _enrich_with_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Add best_price and best_platform columns to a products DataFrame."""
    if df.empty:
        return df
    conn = get_connection()
    try:
        ids = df["product_id"].tolist()
        placeholders = ",".join("?" * len(ids))
        price_df = pd.read_sql_query(
            f"""
            SELECT product_id,
                   MIN(price + delivery_fee + platform_fee + surge_fee - coupon_discount) AS best_total,
                   platform
            FROM platform_prices
            WHERE product_id IN ({placeholders}) AND in_stock=1
            GROUP BY product_id
            """,
            conn, params=ids
        )
    finally:
        conn.close()

    if not price_df.empty:
        df = df.merge(price_df, on="product_id", how="left")
    return df
