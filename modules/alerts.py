"""
PricePulse - Price Alerts Module
Manages creation, monitoring, and notification of price alerts.
"""

import pandas as pd
from datetime import datetime
from utils.db import get_connection, create_price_alert, get_user_alerts, delete_alert
from utils.helpers import PLATFORM_CONFIG, PLATFORM_ORDER, fmt_currency


def create_alert(user_id: str, product_id: str, product_name: str,
                  target_price: float, platform: str = "any") -> dict:
    """
    Create a price alert for a user.

    Parameters
    ----------
    user_id      : Authenticated user's ID.
    product_id   : Product to track.
    product_name : Display name.
    target_price : Price threshold to trigger the alert.
    platform     : Specific platform or "any".

    Returns
    -------
    dict with alert_id and status message.
    """
    alert_id = create_price_alert(
        user_id=user_id,
        product_id=product_id,
        product_name=product_name,
        target_price=target_price,
        platform=platform,
    )
    return {
        "alert_id": alert_id,
        "message": f"✅ Alert set! We'll notify you when {product_name} drops to {fmt_currency(target_price)}.",
    }


def check_alerts(user_id: str) -> list[dict]:
    """
    Check all active alerts for a user against current prices.
    Returns a list of triggered alert dictionaries.
    """
    conn = get_connection()
    try:
        alerts_df = get_user_alerts(user_id)
        if alerts_df.empty:
            return []

        triggered = []
        for _, alert in alerts_df.iterrows():
            product_id   = alert["product_id"]
            target_price = float(alert["target_price"])
            platform     = alert.get("platform", "any")

            # Fetch current prices
            sql = """
                SELECT platform,
                       price + delivery_fee + platform_fee + surge_fee - coupon_discount AS total_cost
                FROM platform_prices
                WHERE product_id = ? AND in_stock = 1
            """
            price_df = pd.read_sql_query(sql, conn, params=(product_id,))
            if price_df.empty:
                continue

            if platform != "any":
                price_df = price_df[price_df["platform"] == platform]

            if price_df.empty:
                continue

            min_price = price_df["total_cost"].min()
            if min_price <= target_price:
                best_platform = price_df.loc[price_df["total_cost"].idxmin(), "platform"]
                cfg = PLATFORM_CONFIG.get(best_platform, {})
                triggered.append({
                    "alert_id": int(alert["alert_id"]),
                    "product_name": alert.get("product_name", ""),
                    "target_price": target_price,
                    "current_price": round(float(min_price), 2),
                    "platform": best_platform,
                    "platform_display": cfg.get("display", ""),
                    "platform_emoji": cfg.get("emoji", ""),
                    "savings": round(target_price - float(min_price), 2),
                })
    finally:
        conn.close()

    return triggered


def get_alerts_with_current_prices(user_id: str) -> pd.DataFrame:
    """
    Return all alerts for a user enriched with current price data.
    """
    conn = get_connection()
    try:
        alerts_df = get_user_alerts(user_id)
        if alerts_df.empty:
            return pd.DataFrame()

        enriched_rows = []
        for _, alert in alerts_df.iterrows():
            product_id = alert["product_id"]

            # Best current price
            row = conn.execute(
                """
                SELECT platform,
                       MIN(price + delivery_fee + platform_fee
                           + surge_fee - coupon_discount) AS current_best
                FROM platform_prices
                WHERE product_id = ? AND in_stock = 1
                GROUP BY platform
                ORDER BY current_best ASC
                LIMIT 1
                """,
                (product_id,)
            ).fetchone()

            current_best = float(row["current_best"]) if row and row["current_best"] else None
            best_platform_key = row["platform"] if row else None

            target = float(alert["target_price"])
            status = "🎯 Triggered!" if (current_best and current_best <= target) else "⏳ Watching"
            price_diff = round((current_best - target), 2) if current_best else None

            enriched_rows.append({
                "alert_id": int(alert["alert_id"]),
                "product_name": alert.get("product_name") or alert.get("pname", ""),
                "brand": alert.get("brand", ""),
                "category": alert.get("category", ""),
                "target_price": target,
                "current_best_price": current_best,
                "price_difference": price_diff,
                "platform": best_platform_key,
                "platform_display": PLATFORM_CONFIG.get(best_platform_key or "", {}).get("display", ""),
                "status": status,
                "created_at": alert.get("created_at", ""),
            })

        return pd.DataFrame(enriched_rows)
    finally:
        conn.close()


def remove_alert(alert_id: int):
    """Deactivate an alert by its ID."""
    delete_alert(alert_id)


def format_alert_notification(alert: dict) -> str:
    """Format a triggered alert as a human-readable notification string."""
    return (
        f"🔔 **Price Alert!** {alert['product_name']} is now "
        f"{fmt_currency(alert['current_price'])} on {alert['platform_display']} "
        f"(your target was {fmt_currency(alert['target_price'])})."
    )
