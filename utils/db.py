"""
PricePulse - Database Utility Module
Handles all SQLite database operations including schema creation,
CRUD operations, and data initialization from CSV files.
"""

import sqlite3
import pandas as pd
import hashlib
import os
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Database path configuration
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "pricepulse.db"
DATA_DIR = BASE_DIR / "data"


def get_connection() -> sqlite3.Connection:
    """
    Returns a SQLite connection with row_factory set to Row
    so columns can be accessed by name.
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ──────────────────────────────────────────────
# Schema Creation
# ──────────────────────────────────────────────
SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name   TEXT,
    city        TEXT,
    pincode     TEXT,
    avatar_url  TEXT,
    preferences TEXT DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login  TIMESTAMP,
    is_active   INTEGER DEFAULT 1
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    brand        TEXT,
    category     TEXT,
    subcategory  TEXT,
    unit         TEXT,
    image_url    TEXT,
    description  TEXT,
    is_popular   INTEGER DEFAULT 0,
    tags         TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Platform prices table
CREATE TABLE IF NOT EXISTS platform_prices (
    price_id         TEXT PRIMARY KEY,
    product_id       TEXT NOT NULL,
    platform         TEXT NOT NULL,
    price            REAL NOT NULL,
    mrp              REAL,
    discount_percent REAL DEFAULT 0,
    delivery_fee     REAL DEFAULT 0,
    platform_fee     REAL DEFAULT 0,
    surge_fee        REAL DEFAULT 0,
    delivery_time_min INTEGER,
    delivery_time_max INTEGER,
    in_stock         INTEGER DEFAULT 1,
    coupon_code      TEXT,
    coupon_discount  REAL DEFAULT 0,
    last_updated     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Search history table
CREATE TABLE IF NOT EXISTS search_history (
    search_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,
    query       TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Price alerts table
CREATE TABLE IF NOT EXISTS price_alerts (
    alert_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    product_id  TEXT NOT NULL,
    product_name TEXT,
    platform    TEXT DEFAULT 'any',
    target_price REAL NOT NULL,
    current_price REAL,
    alert_type  TEXT DEFAULT 'below',
    is_active   INTEGER DEFAULT 1,
    is_triggered INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Saved baskets table
CREATE TABLE IF NOT EXISTS saved_baskets (
    basket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    basket_name TEXT NOT NULL,
    items       TEXT NOT NULL,
    total_zepto REAL,
    total_blinkit REAL,
    total_instamart REAL,
    total_bigbasket REAL,
    cheapest_platform TEXT,
    potential_savings REAL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Analytics / savings tracking table
CREATE TABLE IF NOT EXISTS analytics (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,
    event_type  TEXT NOT NULL,
    product_id  TEXT,
    platform_from TEXT,
    platform_to TEXT,
    amount_saved REAL DEFAULT 0,
    metadata    TEXT DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trending searches (aggregated)
CREATE TABLE IF NOT EXISTS trending_searches (
    trend_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT UNIQUE NOT NULL,
    search_count INTEGER DEFAULT 1,
    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_database():
    """
    Initialises the database: creates tables and loads seed data
    from CSV files if the tables are empty.
    """
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        logger.info("Database schema created / verified.")

        # Seed products
        cursor = conn.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            _seed_products(conn)

        # Seed platform prices
        cursor = conn.execute("SELECT COUNT(*) FROM platform_prices")
        if cursor.fetchone()[0] == 0:
            _seed_prices(conn)

        # Seed demo users
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            _seed_users(conn)

        # Seed trending searches
        cursor = conn.execute("SELECT COUNT(*) FROM trending_searches")
        if cursor.fetchone()[0] == 0:
            _seed_trending(conn)

        logger.info("Database initialisation complete.")
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Seed helpers
# ──────────────────────────────────────────────

def _seed_products(conn: sqlite3.Connection):
    """Load products from CSV into the database."""
    try:
        df = pd.read_csv(DATA_DIR / "products.csv")
        df["is_popular"] = df["is_popular"].apply(lambda x: 1 if str(x).lower() == "true" else 0)
        df.to_sql("products", conn, if_exists="append", index=False)
        logger.info(f"Seeded {len(df)} products.")
    except Exception as e:
        logger.error(f"Error seeding products: {e}")


def _seed_prices(conn: sqlite3.Connection):
    """Load platform prices from CSV into the database."""
    try:
        df = pd.read_csv(DATA_DIR / "prices.csv")
        df["in_stock"] = df["in_stock"].apply(lambda x: 1 if str(x).lower() == "true" else 0)
        # Rename columns to match schema
        df = df.rename(columns={"price_id": "price_id"})
        df.to_sql("platform_prices", conn, if_exists="append", index=False)
        logger.info(f"Seeded {len(df)} price records.")
    except Exception as e:
        logger.error(f"Error seeding prices: {e}")


def _seed_users(conn: sqlite3.Connection):
    """Load demo users with hashed passwords."""
    try:
        df = pd.read_csv(DATA_DIR / "users.csv")
        # Add a default hashed password "password123" for all demo users
        default_hash = hashlib.sha256("password123".encode()).hexdigest()
        df["password_hash"] = default_hash
        df["is_active"] = df["is_active"].apply(lambda x: 1 if str(x).lower() == "true" else 0)
        df["preferences"] = "{}"
        # Keep only schema columns
        cols = ["user_id", "username", "email", "password_hash", "full_name",
                "city", "pincode", "is_active", "preferences"]
        df[cols].to_sql("users", conn, if_exists="append", index=False)
        logger.info(f"Seeded {len(df)} users.")
    except Exception as e:
        logger.error(f"Error seeding users: {e}")


def _seed_trending(conn: sqlite3.Connection):
    """Insert default trending search terms."""
    terms = [
        ("Amul Milk", 1520), ("Maggi Noodles", 1380), ("Bread", 1200),
        ("Eggs", 1100), ("Aashirvaad Atta", 980), ("Tata Salt", 870),
        ("Nescafe Coffee", 760), ("Fortune Oil", 720), ("Parle G", 690),
        ("Basmati Rice", 650),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO trending_searches (query, search_count) VALUES (?, ?)",
        terms,
    )
    conn.commit()


# ──────────────────────────────────────────────
# Query helpers
# ──────────────────────────────────────────────

def search_products(query: str, limit: int = 20) -> pd.DataFrame:
    """Full-text search on product name, brand, category, tags."""
    conn = get_connection()
    try:
        like = f"%{query.lower()}%"
        sql = """
            SELECT p.*, pp.price as min_price, pp.platform as cheapest_platform
            FROM products p
            LEFT JOIN (
                SELECT product_id,
                       MIN(price + delivery_fee + platform_fee + surge_fee - coupon_discount) as price,
                       platform
                FROM platform_prices
                WHERE in_stock = 1
                GROUP BY product_id
            ) pp ON p.product_id = pp.product_id
            WHERE LOWER(p.product_name) LIKE ?
               OR LOWER(p.brand) LIKE ?
               OR LOWER(p.category) LIKE ?
               OR LOWER(p.tags) LIKE ?
            LIMIT ?
        """
        df = pd.read_sql_query(sql, conn, params=(like, like, like, like, limit))
        return df
    finally:
        conn.close()


def get_product_prices(product_id: str) -> pd.DataFrame:
    """Get all platform prices for a specific product."""
    conn = get_connection()
    try:
        sql = """
            SELECT pp.*, p.product_name, p.brand, p.category, p.image_url, p.unit
            FROM platform_prices pp
            JOIN products p ON pp.product_id = p.product_id
            WHERE pp.product_id = ?
            ORDER BY pp.price ASC
        """
        return pd.read_sql_query(sql, conn, params=(product_id,))
    finally:
        conn.close()


def get_popular_products(limit: int = 8) -> pd.DataFrame:
    """Fetch popular products with their best price."""
    conn = get_connection()
    try:
        sql = """
            SELECT p.*,
                   MIN(pp.price + pp.delivery_fee + pp.platform_fee
                       + pp.surge_fee - pp.coupon_discount) as best_total,
                   pp.platform as best_platform,
                   pp.price as best_price
            FROM products p
            LEFT JOIN platform_prices pp ON p.product_id = pp.product_id
            WHERE p.is_popular = 1 AND pp.in_stock = 1
            GROUP BY p.product_id
            LIMIT ?
        """
        return pd.read_sql_query(sql, conn, params=(limit,))
    finally:
        conn.close()


def get_trending_searches(limit: int = 10) -> list:
    """Return top trending search queries."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT query, search_count FROM trending_searches "
            "ORDER BY search_count DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def log_search(user_id: str | None, query: str, results_count: int = 0):
    """Record a search event and update trending."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO search_history (user_id, query, results_count) VALUES (?,?,?)",
            (user_id, query, results_count)
        )
        conn.execute(
            """INSERT INTO trending_searches (query, search_count)
               VALUES (?, 1)
               ON CONFLICT(query) DO UPDATE SET
                   search_count = search_count + 1,
                   last_searched = CURRENT_TIMESTAMP""",
            (query,)
        )
        conn.commit()
    finally:
        conn.close()


def get_user_search_history(user_id: str, limit: int = 10) -> list:
    """Return recent searches for a user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT query, searched_at FROM search_history "
            "WHERE user_id = ? ORDER BY searched_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Price Alerts ─────────────────────────────

def create_price_alert(user_id: str, product_id: str, product_name: str,
                        target_price: float, platform: str = "any",
                        alert_type: str = "below") -> int:
    """Create a price alert and return its ID."""
    conn = get_connection()
    try:
        # Get current best price for the product
        row = conn.execute(
            "SELECT MIN(price) FROM platform_prices WHERE product_id = ? AND in_stock = 1",
            (product_id,)
        ).fetchone()
        current_price = row[0] if row[0] else 0.0

        cursor = conn.execute(
            """INSERT INTO price_alerts
               (user_id, product_id, product_name, platform, target_price,
                current_price, alert_type)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, product_id, product_name, platform, target_price,
             current_price, alert_type)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_alerts(user_id: str) -> pd.DataFrame:
    """Fetch all active alerts for a user."""
    conn = get_connection()
    try:
        sql = """
            SELECT pa.*, p.product_name as pname, p.brand, p.category
            FROM price_alerts pa
            JOIN products p ON pa.product_id = p.product_id
            WHERE pa.user_id = ? AND pa.is_active = 1
            ORDER BY pa.created_at DESC
        """
        return pd.read_sql_query(sql, conn, params=(user_id,))
    finally:
        conn.close()


def delete_alert(alert_id: int):
    """Delete (deactivate) a price alert."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE price_alerts SET is_active = 0 WHERE alert_id = ?",
            (alert_id,)
        )
        conn.commit()
    finally:
        conn.close()


# ── Baskets ───────────────────────────────────

def save_basket(user_id: str, basket_name: str, items: str,
                totals: dict) -> int:
    """Persist a basket comparison result."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO saved_baskets
               (user_id, basket_name, items, total_zepto, total_blinkit,
                total_instamart, total_bigbasket, cheapest_platform, potential_savings)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, basket_name, items,
             totals.get("zepto", 0), totals.get("blinkit", 0),
             totals.get("instamart", 0), totals.get("bigbasket", 0),
             totals.get("cheapest_platform", ""),
             totals.get("potential_savings", 0))
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_baskets(user_id: str) -> pd.DataFrame:
    """Return saved baskets for a user."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM saved_baskets WHERE user_id = ? ORDER BY created_at DESC",
            conn, params=(user_id,)
        )
    finally:
        conn.close()


# ── Analytics ────────────────────────────────

def log_savings_event(user_id: str, product_id: str,
                       platform_from: str, platform_to: str, amount_saved: float):
    """Record a savings event for dashboard analytics."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO analytics
               (user_id, event_type, product_id, platform_from, platform_to, amount_saved)
               VALUES (?,?,?,?,?,?)""",
            (user_id, "savings", product_id, platform_from, platform_to, amount_saved)
        )
        conn.commit()
    finally:
        conn.close()


def get_savings_summary(user_id: str) -> dict:
    """Return aggregated savings stats for a user."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT
                   COUNT(*) as total_comparisons,
                   COALESCE(SUM(amount_saved), 0) as total_saved,
                   COALESCE(AVG(amount_saved), 0) as avg_saved,
                   COALESCE(MAX(amount_saved), 0) as max_saved
               FROM analytics
               WHERE user_id = ? AND event_type = 'savings'""",
            (user_id,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_platform_stats() -> pd.DataFrame:
    """Return price stats per platform for market-share charts."""
    conn = get_connection()
    try:
        sql = """
            SELECT platform,
                   COUNT(*) as product_count,
                   AVG(price) as avg_price,
                   AVG(delivery_fee) as avg_delivery,
                   SUM(CASE WHEN in_stock=1 THEN 1 ELSE 0 END) as in_stock_count
            FROM platform_prices
            GROUP BY platform
        """
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def get_biggest_savings(limit: int = 5) -> pd.DataFrame:
    """Products with the highest savings potential across platforms."""
    conn = get_connection()
    try:
        sql = """
            SELECT p.product_name, p.brand, p.category,
                   MAX(pp.price) as max_price,
                   MIN(pp.price) as min_price,
                   MAX(pp.price) - MIN(pp.price) as savings,
                   ROUND((MAX(pp.price) - MIN(pp.price)) * 100.0 / MAX(pp.price), 1) as savings_pct
            FROM products p
            JOIN platform_prices pp ON p.product_id = pp.product_id
            WHERE pp.in_stock = 1
            GROUP BY p.product_id
            HAVING COUNT(DISTINCT pp.platform) >= 2
            ORDER BY savings DESC
            LIMIT ?
        """
        return pd.read_sql_query(sql, conn, params=(limit,))
    finally:
        conn.close()


# ── Auth helpers ─────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, email: str, password: str,
                full_name: str = "", city: str = "") -> dict:
    """Register a new user. Returns user dict or raises on duplicate."""
    conn = get_connection()
    try:
        import uuid
        user_id = f"U{uuid.uuid4().hex[:8].upper()}"
        conn.execute(
            """INSERT INTO users (user_id, username, email, password_hash, full_name, city)
               VALUES (?,?,?,?,?,?)""",
            (user_id, username, email, hash_password(password), full_name, city)
        )
        conn.commit()
        return {"user_id": user_id, "username": username, "email": email, "full_name": full_name}
    except sqlite3.IntegrityError as e:
        raise ValueError(f"Username or email already exists: {e}")
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials and return user dict or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE (username=? OR email=?) AND is_active=1",
            (username, username)
        ).fetchone()
        if row and row["password_hash"] == hash_password(password):
            conn.execute(
                "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE user_id=?",
                (row["user_id"],)
            )
            conn.commit()
            return dict(row)
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT user_id, username, email, full_name, city, pincode, created_at, last_login "
            "FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_profile(user_id: str, full_name: str, city: str, pincode: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET full_name=?, city=?, pincode=? WHERE user_id=?",
            (full_name, city, pincode, user_id)
        )
        conn.commit()
    finally:
        conn.close()
