"""
PricePulse - Home Page
Displays hero search bar, popular products, trending searches,
biggest savings today, and recent search history.
"""

import streamlit as st
import pandas as pd
from utils.helpers import inject_global_css, render_sidebar_logo, PLATFORM_CONFIG, fmt_currency, get_category_icon
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in
from utils.db import get_trending_searches, get_biggest_savings, get_user_search_history, init_database
from modules.search_engine import get_popular_products
from modules.recommendation_engine import get_best_deals


# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Home",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init DB ────────────────────────────────────
init_database()

# ── Global CSS ─────────────────────────────────
inject_global_css()

# ── Sidebar ────────────────────────────────────
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


# ── Hero Section ───────────────────────────────
st.markdown("""
<div class="pp-hero">
    <div style="font-size:3rem;">💜</div>
    <h1>PricePulse</h1>
    <p>Compare grocery prices across Zepto, Blinkit, Instamart & BigBasket</p>
    <p style="font-size:0.9rem; color:#7C3AED; margin-top:0.5rem;">
        ⚡ Real-time comparison &nbsp;|&nbsp;
        💰 Find cheapest price &nbsp;|&nbsp;
        🛒 Optimise your basket
    </p>
</div>
""", unsafe_allow_html=True)

# ── Search Bar ─────────────────────────────────
col_search, col_btn = st.columns([5, 1])
with col_search:
    search_query = st.text_input(
        "Search for products",
        placeholder="🔍  Try  'Amul Milk',  'Maggi',  'Sunflower Oil' …",
        label_visibility="collapsed",
        key="home_search",
    )
with col_btn:
    search_btn = st.button("Search →", use_container_width=True)

if search_btn and search_query:
    st.switch_page("pages/2_🔍_Product_Search.py")

st.markdown("<br>", unsafe_allow_html=True)

# ── Platform chips ──────────────────────────────
st.markdown("##### 🏪 Compare across India's top quick-commerce apps")
cols = st.columns(4)
for i, (key, cfg) in enumerate(PLATFORM_CONFIG.items()):
    with cols[i]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{cfg['bg_color']},{cfg['color']}22);
                    border:1px solid {cfg['color']}55; border-radius:14px;
                    padding:1rem; text-align:center;">
            <div style="font-size:2rem;">{cfg['emoji']}</div>
            <div style="font-weight:700; color:{cfg['color']}; font-size:1rem;">{cfg['display']}</div>
            <div style="font-size:0.75rem; color:#9CA3AF;">{cfg['tagline']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Main content columns ────────────────────────
left_col, right_col = st.columns([2, 1])

with left_col:
    # ── Popular Products ────────────────────────
    st.markdown("### 🌟 Popular Products")
    pop_df = get_popular_products(8)
    if not pop_df.empty:
        prod_cols = st.columns(4)
        for i, (_, prod) in enumerate(pop_df.iterrows()):
            col = prod_cols[i % 4]
            with col:
                icon = get_category_icon(str(prod.get("category", "")))
                best_price = prod.get("best_total") or prod.get("best_price") or 0
                platform_key = prod.get("best_platform", "")
                plat_cfg = PLATFORM_CONFIG.get(platform_key, {})
                plat_color = plat_cfg.get("color", "#7C3AED")
                plat_name  = plat_cfg.get("display", "")

                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1E103A,#2D1B4E);
                            border:1px solid #3D2B5E; border-radius:14px;
                            padding:1rem; margin-bottom:0.8rem; cursor:pointer;
                            transition:all 0.2s ease;">
                    <div style="font-size:2rem; text-align:center;">{icon}</div>
                    <div style="font-weight:600; font-size:0.85rem; color:#E2E8F0;
                                text-align:center; margin:0.4rem 0; line-height:1.3;">
                        {str(prod.get('product_name',''))[:25]}
                    </div>
                    <div style="text-align:center; font-size:0.75rem; color:#9CA3AF;">
                        {prod.get('brand','')}
                    </div>
                    <div style="text-align:center; margin-top:0.5rem;">
                        <span style="color:#4ADE80; font-weight:700; font-size:1rem;">
                            ₹{best_price:.0f}
                        </span>
                    </div>
                    <div style="text-align:center; font-size:0.7rem; margin-top:0.3rem;">
                        <span style="color:{plat_color};">{plat_name}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Loading popular products…")

    # ── Best Deals Today ───────────────────────
    st.markdown("### 🔥 Biggest Savings Today")
    deals_df = get_best_deals(5)
    if not deals_df.empty:
        for _, deal in deals_df.iterrows():
            plat_cfg = PLATFORM_CONFIG.get(deal.get("best_platform", ""), {})
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1A0030,#2D1B4E);
                        border:1px solid #4ADE8033; border-radius:14px;
                        padding:1rem 1.2rem; margin-bottom:0.6rem;
                        display:flex; align-items:center; gap:1rem;">
                <div style="flex:1;">
                    <div style="font-weight:600; color:#E2E8F0;">
                        {str(deal.get('product_name',''))[:35]}
                    </div>
                    <div style="font-size:0.75rem; color:#9CA3AF;">
                        {deal.get('brand','')} &bull; {deal.get('category','')}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#4ADE80; font-weight:700; font-size:1.1rem;">
                        Save ₹{deal.get('savings_amount',0):.0f}
                    </div>
                    <div style="font-size:0.75rem; color:#A78BFA;">
                        {plat_cfg.get('emoji','')} {plat_cfg.get('display','')}
                    </div>
                </div>
                <div style="background:#4ADE8022; border:1px solid #4ADE80;
                            border-radius:8px; padding:4px 10px;
                            color:#4ADE80; font-weight:700; font-size:0.85rem;">
                    {deal.get('savings_pct',0):.0f}% OFF
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Loading deals…")


with right_col:
    # ── Trending Searches ───────────────────────
    st.markdown("### 📈 Trending Searches")
    trends = get_trending_searches(10)
    for i, trend in enumerate(trends):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
        count = trend.get("search_count", 0)
        query = trend.get("query", "")
        st.markdown(f"""
        <div style="background:#1E103A; border:1px solid #2D1B4E; border-radius:10px;
                    padding:0.6rem 1rem; margin-bottom:0.5rem;
                    display:flex; justify-content:space-between; align-items:center;">
            <span style="color:#E2E8F0;">{medal} {query}</span>
            <span style="color:#9CA3AF; font-size:0.75rem;">{count:,} searches</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Recent Searches (if logged in) ──────────
    if is_logged_in():
        user = get_current_user()
        st.markdown("### 🕐 Recent Searches")
        history = get_user_search_history(user["user_id"], 5)
        if history:
            for item in history:
                st.markdown(f"""
                <div style="background:#1E103A; border:1px solid #2D1B4E; border-radius:8px;
                            padding:0.5rem 1rem; margin-bottom:0.4rem;
                            font-size:0.85rem; color:#C4B5FD;">
                    🔍 {item.get('query','')}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No recent searches yet.")

    # ── Quick Stats ─────────────────────────────
    st.markdown("### ⚡ Quick Stats")
    conn_check = True
    try:
        from utils.db import get_connection
        conn = get_connection()
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        conn.close()
    except Exception:
        total = 50
        conn_check = False

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E0A3C,#2D1463);
                border:1px solid #3D2B5E; border-radius:14px; padding:1.2rem;">
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.8rem;">
            <div style="text-align:center;">
                <div style="font-size:1.5rem; font-weight:800; color:#A78BFA;">{total}</div>
                <div style="font-size:0.7rem; color:#9CA3AF;">Products</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem; font-weight:800; color:#4ADE80;">4</div>
                <div style="font-size:0.7rem; color:#9CA3AF;">Platforms</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem; font-weight:800; color:#F59E0B;">10 min</div>
                <div style="font-size:0.7rem; color:#9CA3AF;">Fastest Delivery</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem; font-weight:800; color:#F472B6;">₹50</div>
                <div style="font-size:0.7rem; color:#9CA3AF;">Avg. Savings</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; color:#4B5563; font-size:0.8rem; padding:1rem 0;
            border-top:1px solid #1F2937;">
    PricePulse &copy; 2024 &nbsp;|&nbsp; Built with ❤️ using Streamlit &nbsp;|&nbsp;
    Prices updated every hour
</div>
""", unsafe_allow_html=True)
