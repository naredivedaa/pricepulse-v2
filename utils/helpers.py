"""
PricePulse - Helper Utilities
Formatting, styling, platform metadata, and reusable UI components.
"""

import streamlit as st
import pandas as pd
from typing import Optional


# ──────────────────────────────────────────────
# Platform Metadata
# ──────────────────────────────────────────────

PLATFORM_CONFIG = {
    "zepto": {
        "display": "Zepto",
        "color": "#8B2FC9",
        "bg_color": "#1A0A2E",
        "emoji": "⚡",
        "logo": "Z",
        "tagline": "Delivery in 10 mins",
        "free_delivery_threshold": 149,
    },
    "blinkit": {
        "display": "Blinkit",
        "color": "#F5A623",
        "bg_color": "#1A1200",
        "emoji": "🟡",
        "logo": "B",
        "tagline": "Blink and it's there",
        "free_delivery_threshold": 199,
    },
    "instamart": {
        "display": "Swiggy Instamart",
        "color": "#FC8019",
        "bg_color": "#1A0A00",
        "emoji": "🛒",
        "logo": "I",
        "tagline": "Groceries at your door",
        "free_delivery_threshold": 199,
    },
    "bigbasket": {
        "display": "BigBasket",
        "color": "#84C225",
        "bg_color": "#0A1400",
        "emoji": "🧺",
        "logo": "BB",
        "tagline": "India's Biggest Online Supermarket",
        "free_delivery_threshold": 500,
    },
}

PLATFORM_ORDER = ["zepto", "blinkit", "instamart", "bigbasket"]

CATEGORY_ICONS = {
    "Dairy": "🥛",
    "Grains": "🌾",
    "Instant Food": "🍜",
    "Spices": "🧂",
    "Snacks": "🍪",
    "Beverages": "☕",
    "Oils": "🫙",
    "Personal Care": "🧴",
    "Home Care": "🧹",
    "Spreads": "🍯",
    "Condiments": "🥫",
    "Health": "💊",
    "Hair Care": "💆",
    "Stationery": "📎",
    "Chocolates": "🍫",
    "Default": "📦",
}


def fmt_currency(amount: float) -> str:
    """Format a number as Indian Rupees."""
    return f"₹{amount:,.2f}"


def fmt_pct(value: float) -> str:
    """Format a float as a percentage string."""
    return f"{value:.1f}%"


def get_category_icon(category: str) -> str:
    return CATEGORY_ICONS.get(category, CATEGORY_ICONS["Default"])


def platform_badge(platform: str) -> str:
    """Return a styled HTML badge string for a platform."""
    cfg = PLATFORM_CONFIG.get(platform, {})
    color = cfg.get("color", "#888")
    name = cfg.get("display", platform.title())
    emoji = cfg.get("emoji", "🏪")
    return f'<span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:0.8rem;font-weight:600;">{emoji} {name}</span>'


def compute_total_cost(row: pd.Series) -> float:
    """Compute total landed cost from a price row."""
    total = (
        float(row.get("price", 0))
        + float(row.get("delivery_fee", 0))
        + float(row.get("platform_fee", 0))
        + float(row.get("surge_fee", 0))
        - float(row.get("coupon_discount", 0))
    )
    return round(max(total, 0), 2)


def get_cheapest_platform(prices_df: pd.DataFrame) -> Optional[str]:
    """Given a DataFrame of prices, return the platform with the lowest total cost."""
    if prices_df.empty:
        return None
    prices_df = prices_df[prices_df["in_stock"] == 1].copy()
    if prices_df.empty:
        return None
    prices_df["total_cost"] = prices_df.apply(compute_total_cost, axis=1)
    idx = prices_df["total_cost"].idxmin()
    return prices_df.loc[idx, "platform"]


def savings_tag(original: float, discounted: float) -> str:
    """HTML savings badge."""
    if original <= 0:
        return ""
    saved = original - discounted
    pct = (saved / original) * 100
    if saved <= 0:
        return ""
    return (
        f'<span style="background:#16a34a;color:#fff;padding:2px 8px;'
        f'border-radius:8px;font-size:0.75rem;font-weight:700;">'
        f'Save {fmt_currency(saved)} ({pct:.0f}%)</span>'
    )


def delivery_time_tag(min_t: int, max_t: int) -> str:
    """Return a friendly delivery time string."""
    if min_t and max_t:
        return f"🕐 {min_t}–{max_t} mins"
    return "🕐 N/A"


def get_page_config() -> dict:
    """Standard Streamlit page config kwargs."""
    return {
        "page_title": "PricePulse – Smart Grocery Comparison",
        "page_icon": "💜",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }


def inject_global_css():
    """Inject the global dark-mode CSS theme into the Streamlit app."""
    st.markdown("""
    <style>
    /* ── Global Reset & Font ───────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #0F0F1A !important;
        color: #E2E8F0 !important;
    }

    /* ── Sidebar ────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #13001F 0%, #1A0030 100%) !important;
        border-right: 1px solid #2D1B4E !important;
    }
    section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }

    /* ── Main Content ───────────────────────────── */
    .main .block-container {
        padding: 1.5rem 2rem !important;
        max-width: 1400px !important;
    }

    /* ── Metrics / KPI Cards ────────────────────── */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1E103A 0%, #2D1B4E 100%) !important;
        border: 1px solid #3D2B5E !important;
        border-radius: 16px !important;
        padding: 1.2rem !important;
    }
    [data-testid="stMetricValue"] { color: #A78BFA !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"]  { color: #4ADE80 !important; }

    /* ── Buttons ────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #7C3AED, #9D5FFF) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #6D28D9, #7C3AED) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4) !important;
    }

    /* ── Input Fields ───────────────────────────── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stNumberInput input {
        background-color: #1E103A !important;
        border: 1px solid #3D2B5E !important;
        border-radius: 10px !important;
        color: #E2E8F0 !important;
    }

    /* ── DataFrames ─────────────────────────────── */
    .stDataFrame, .dataframe {
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    /* ── Expander ───────────────────────────────── */
    .streamlit-expanderHeader {
        background-color: #1E103A !important;
        border-radius: 10px !important;
    }

    /* ── Tabs ───────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1E103A !important;
        border-radius: 12px !important;
        padding: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #9CA3AF !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7C3AED, #9D5FFF) !important;
        color: white !important;
    }

    /* ── Cards ──────────────────────────────────── */
    .pp-card {
        background: linear-gradient(135deg, #1E103A 0%, #2D1B4E 100%);
        border: 1px solid #3D2B5E;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .pp-card-highlight {
        background: linear-gradient(135deg, #3D0F8A 0%, #5B21B6 100%);
        border: 2px solid #7C3AED;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* ── Hero section ───────────────────────────── */
    .pp-hero {
        background: linear-gradient(135deg, #1E0A3C 0%, #2D1463 50%, #1A0030 100%);
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #3D2B5E;
    }
    .pp-hero h1 { font-size: 2.8rem; font-weight: 800; color: #A78BFA; margin: 0; }
    .pp-hero p  { font-size: 1.2rem; color: #C4B5FD; margin-top: 0.5rem; }

    /* ── Platform price card ────────────────────── */
    .platform-card {
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    .platform-card:hover { transform: translateY(-2px); }
    .platform-card.cheapest { border: 2px solid #4ADE80 !important; }

    /* ── Chat bubbles ───────────────────────────── */
    .chat-user {
        background: linear-gradient(135deg, #7C3AED, #9D5FFF);
        border-radius: 18px 18px 4px 18px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        max-width: 75%;
        margin-left: auto;
        color: white;
    }
    .chat-ai {
        background: #1E103A;
        border: 1px solid #3D2B5E;
        border-radius: 18px 18px 18px 4px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        max-width: 75%;
        color: #E2E8F0;
    }

    /* ── Alerts ─────────────────────────────────── */
    .stAlert > div { border-radius: 12px !important; }

    /* ── Progress bar ───────────────────────────── */
    .stProgress > div > div { background-color: #7C3AED !important; }

    /* ── Divider ────────────────────────────────── */
    hr { border-color: #2D1B4E !important; }

    /* ── Scrollbar ──────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0F0F1A; }
    ::-webkit-scrollbar-thumb { background: #3D2B5E; border-radius: 3px; }

    /* ── Hide Streamlit default footer / header ─── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar_logo():
    """Render the PricePulse logo in the sidebar."""
    st.sidebar.markdown("""
    <div style="text-align:center; padding: 1.5rem 0 1rem 0;">
        <div style="font-size:2.5rem;">💜</div>
        <div style="font-size:1.6rem; font-weight:800;
                    background: linear-gradient(135deg, #A78BFA, #7C3AED);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;">
            PricePulse
        </div>
        <div style="font-size:0.75rem; color:#9CA3AF; margin-top:0.2rem;">
            Smart Grocery Comparison
        </div>
    </div>
    <hr style="border-color:#2D1B4E; margin:0 0 1rem 0;">
    """, unsafe_allow_html=True)


def render_platform_price_card(row: pd.Series, is_cheapest: bool = False):
    """Render a single platform price card as HTML."""
    platform = row.get("platform", "")
    cfg = PLATFORM_CONFIG.get(platform, {})
    color = cfg.get("color", "#7C3AED")
    emoji = cfg.get("emoji", "🏪")
    display = cfg.get("display", platform.title())
    tagline = cfg.get("tagline", "")

    total = compute_total_cost(row)
    delivery_fee = float(row.get("delivery_fee", 0))
    platform_fee = float(row.get("platform_fee", 0))
    coupon = float(row.get("coupon_discount", 0))
    time_str = delivery_time_tag(
        int(row.get("delivery_time_min", 0) or 0),
        int(row.get("delivery_time_max", 0) or 0)
    )

    cheapest_badge = (
        '<span style="background:#16a34a;color:#fff;padding:2px 8px;'
        'border-radius:8px;font-size:0.7rem;font-weight:700;margin-left:8px;">✅ CHEAPEST</span>'
        if is_cheapest else ""
    )
    border = f"2px solid #4ADE80" if is_cheapest else f"1px solid {color}33"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1E103A, #2D1B4E);
                border:{border}; border-radius:16px; padding:1.2rem;
                margin-bottom:0.8rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:1.5rem;">{emoji}</span>
                <span style="font-size:1.1rem; font-weight:700; color:{color};
                             margin-left:8px;">{display}</span>
                {cheapest_badge}
                <div style="font-size:0.75rem; color:#9CA3AF; margin-top:4px;">
                    {tagline} &nbsp;|&nbsp; {time_str}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.8rem; font-weight:800; color:#E2E8F0;">
                    ₹{total:.0f}
                </div>
                <div style="font-size:0.75rem; color:#9CA3AF;">Total cost</div>
            </div>
        </div>
        <div style="display:flex; gap:1.5rem; margin-top:0.8rem;
                    padding-top:0.8rem; border-top:1px solid #3D2B5E;
                    font-size:0.8rem; color:#C4B5FD;">
            <span>🏷️ Price: ₹{float(row.get('price',0)):.0f}</span>
            <span>🚚 Delivery: ₹{delivery_fee:.0f}</span>
            <span>💳 Fee: ₹{platform_fee:.0f}</span>
            {'<span>🎫 Coupon: -₹' + f"{coupon:.0f}</span>" if coupon > 0 else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_loading_spinner(text: str = "Comparing prices…"):
    """Context manager-compatible spinner with custom text."""
    return st.spinner(text)
