"""
PricePulse - Savings Dashboard Page
Platform analytics, market share, savings trends,
category breakdown, and personal savings KPIs.
"""

import streamlit as st
import pandas as pd
from utils.helpers import inject_global_css, render_sidebar_logo, PLATFORM_CONFIG, fmt_currency
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in
from utils.db import init_database, get_biggest_savings, get_platform_stats
from modules.analytics import (
    get_platform_kpis, get_user_kpis,
    build_platform_market_share_chart,
    build_avg_price_by_platform_chart,
    build_biggest_savings_chart,
    build_category_savings_chart,
    build_savings_trend_chart,
    build_platform_delivery_radar,
)


# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_database()
inject_global_css()
render_sidebar_logo()
render_sidebar_auth()

st.sidebar.markdown("### 🗂️ Navigation")
st.sidebar.page_link("pages/1_🏠_Home.py",             label="🏠 Home")
st.sidebar.page_link("pages/2_🔍_Product_Search.py",   label="🔍 Product Search")
st.sidebar.page_link("pages/3_🛒_Basket_Comparison.py", label="🛒 Basket Comparison")
st.sidebar.page_link("pages/4_🤖_AI_Assistant.py",      label="🤖 AI Assistant")
st.sidebar.page_link("pages/5_🔔_Price_Alerts.py",      label="🔔 Price Alerts")
st.sidebar.page_link("pages/6_📊_Savings_Dashboard.py", label="📊 Savings Dashboard")
st.sidebar.page_link("pages/7_👤_Profile.py",           label="👤 Profile")


# ── Header ──────────────────────────────────────
st.markdown("## 📊 Savings Dashboard")
st.markdown("Platform analytics, price trends, and your personal savings summary.")

# ── Platform KPIs ───────────────────────────────
kpis = get_platform_kpis()
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("📦 Products", f"{kpis.get('total_products', 0):,}")
with k2:
    st.metric("🏪 Platforms", kpis.get("platforms", 4))
with k3:
    st.metric("💰 Avg Savings", fmt_currency(kpis.get("avg_savings", 0)))
with k4:
    st.metric("🔍 Total Searches", f"{kpis.get('total_searches', 0):,}")
with k5:
    st.metric("🔔 Active Alerts", f"{kpis.get('total_alerts', 0):,}")

st.markdown("---")

# ── User-specific KPIs (if logged in) ──────────
if is_logged_in():
    user = get_current_user()
    user_kpis = get_user_kpis(user["user_id"])

    st.markdown("### 👤 Your Activity")
    u1, u2, u3, u4 = st.columns(4)
    with u1:
        st.metric("🔍 Your Searches", user_kpis.get("searches", 0))
    with u2:
        st.metric("🔔 Active Alerts", user_kpis.get("active_alerts", 0))
    with u3:
        st.metric("🧺 Saved Baskets", user_kpis.get("saved_baskets", 0))
    with u4:
        st.metric("💰 Total Saved", fmt_currency(user_kpis.get("total_saved", 0)))

    # Savings trend (personalised when data exists)
    st.plotly_chart(
        build_savings_trend_chart(user["user_id"]),
        use_container_width=True, key="user_savings_trend"
    )

    st.markdown("---")

# ── Charts Section ──────────────────────────────
st.markdown("### 🏪 Platform Insights")

row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    st.plotly_chart(
        build_platform_market_share_chart(),
        use_container_width=True, key="market_share"
    )
with row1_col2:
    st.plotly_chart(
        build_avg_price_by_platform_chart(),
        use_container_width=True, key="avg_prices"
    )

st.markdown("---")
st.markdown("### 💰 Savings Opportunities")

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.plotly_chart(
        build_biggest_savings_chart(),
        use_container_width=True, key="biggest_savings"
    )
with row2_col2:
    st.plotly_chart(
        build_category_savings_chart(),
        use_container_width=True, key="cat_savings"
    )

st.markdown("---")
st.markdown("### 🎯 Platform Performance")
row3_col1, row3_col2 = st.columns([1, 1])
with row3_col1:
    st.plotly_chart(
        build_platform_delivery_radar(),
        use_container_width=True, key="radar"
    )
with row3_col2:
    # Platform stats table
    st.markdown("#### 📋 Platform Stats Summary")
    stats_df = get_platform_stats()
    if not stats_df.empty:
        display_stats = stats_df.copy()
        display_stats["Platform"] = display_stats["platform"].apply(
            lambda p: f"{PLATFORM_CONFIG.get(p,{}).get('emoji','')} "
                      f"{PLATFORM_CONFIG.get(p,{}).get('display','')}"
        )
        display_stats["Avg Price"] = display_stats["avg_price"].apply(lambda x: f"₹{x:.0f}")
        display_stats["Avg Delivery"] = display_stats["avg_delivery"].apply(lambda x: f"₹{x:.0f}")
        display_stats["In Stock"] = display_stats["in_stock_count"].astype(int)
        display_stats["Products"] = display_stats["product_count"].astype(int)

        st.dataframe(
            display_stats[["Platform", "Products", "In Stock", "Avg Price", "Avg Delivery"]],
            use_container_width=True,
            hide_index=True,
        )

        # Platform comparison cards
        st.markdown("#### 🏆 Platform Rankings")
        platform_rankings = [
            ("⚡ Fastest Delivery", "zepto",     "8-12 min"),
            ("💰 Lowest Avg Price", "bigbasket",  "Best value"),
            ("📦 Most Products",   "bigbasket",  "Widest range"),
            ("🎫 Best Discounts",  "instamart",  "Swiggy offers"),
        ]
        for label, plat, detail in platform_rankings:
            cfg = PLATFORM_CONFIG.get(plat, {})
            st.markdown(f"""
            <div style="background:#1E103A; border:1px solid #3D2B5E; border-radius:10px;
                        padding:0.6rem 1rem; margin-bottom:0.4rem;
                        display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#9CA3AF; font-size:0.85rem;">{label}</span>
                <span>
                    <span style="color:{cfg.get('color','#A78BFA')}; font-weight:600;">
                        {cfg.get('emoji','')} {cfg.get('display','')}
                    </span>
                    <span style="color:#9CA3AF; font-size:0.75rem; margin-left:8px;">{detail}</span>
                </span>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ── Biggest Savings Table ───────────────────────
st.markdown("### 🏆 Top 10 Products with Biggest Price Differences")
savings_df = get_biggest_savings(10)
if not savings_df.empty:
    display_df = savings_df.copy()
    display_df["Max Savings"] = display_df["savings"].apply(lambda x: f"₹{x:.0f}")
    display_df["Savings %"]   = display_df["savings_pct"].apply(lambda x: f"{x:.1f}%")
    display_df["Max Price"]   = display_df["max_price"].apply(lambda x: f"₹{x:.0f}")
    display_df["Min Price"]   = display_df["min_price"].apply(lambda x: f"₹{x:.0f}")

    st.dataframe(
        display_df[["product_name", "brand", "category", "Min Price", "Max Price",
                    "Max Savings", "Savings %"]],
        use_container_width=True,
        hide_index=True,
    )

# ── Footer ──────────────────────────────────────
st.markdown("---")
st.caption(
    "📊 Data refreshes hourly. Prices may vary based on location, time, and platform promotions."
)
