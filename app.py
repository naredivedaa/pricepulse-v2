"""
PricePulse - Main Entry Point
Quick-Commerce Price Comparison Platform

Run with:
    streamlit run app.py

Author  : PricePulse Team
Version : 1.0.0
License : MIT
"""

import streamlit as st
import sys
import os

# ── Ensure project root is on path ────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Lazy import to keep startup fast ──────────────
from utils.db import init_database
from utils.helpers import inject_global_css, render_sidebar_logo, PLATFORM_CONFIG
from utils.auth import render_sidebar_auth, is_logged_in, get_current_user

# ──────────────────────────────────────────────────
# Streamlit page configuration (must be first call)
# ──────────────────────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Smart Grocery Comparison",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help":     "https://github.com/pricepulse/pricepulse",
        "Report a bug": "https://github.com/pricepulse/pricepulse/issues",
        "About":        "# PricePulse\nSmart grocery price comparison across India's top quick-commerce platforms.",
    },
)

# ──────────────────────────────────────────────────
# Database initialisation (runs once per session)
# ──────────────────────────────────────────────────
if "db_initialised" not in st.session_state:
    with st.spinner("⚙️ Initialising PricePulse…"):
        init_database()
    st.session_state["db_initialised"] = True

# ──────────────────────────────────────────────────
# Global theme injection
# ──────────────────────────────────────────────────
inject_global_css()

# ──────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────
render_sidebar_logo()
render_sidebar_auth()

st.sidebar.markdown("### 🗂️ Navigation")
st.sidebar.page_link("app.py",                         label="🏠 Home")
st.sidebar.page_link("pages/2_🔍_Product_Search.py",   label="🔍 Product Search")
st.sidebar.page_link("pages/3_🛒_Basket_Comparison.py", label="🛒 Basket Comparison")
st.sidebar.page_link("pages/4_🤖_AI_Assistant.py",      label="🤖 AI Assistant")
st.sidebar.page_link("pages/5_🔔_Price_Alerts.py",      label="🔔 Price Alerts")
st.sidebar.page_link("pages/6_📊_Savings_Dashboard.py", label="📊 Savings Dashboard")
st.sidebar.page_link("pages/7_👤_Profile.py",           label="👤 Profile")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='text-align:center; color:#6B7280; font-size:0.75rem;'>"
    "v1.0.0 &copy; 2024 PricePulse</div>",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────
# Hero section
# ──────────────────────────────────────────────────
st.markdown("""
<div class="pp-hero">
    <div style="font-size:4rem; animation: pulse 2s infinite;">💜</div>
    <h1 style="font-size:3.5rem;">PricePulse</h1>
    <p style="font-size:1.3rem;">
        India's Smartest Quick-Commerce Price Comparison Platform
    </p>
    <p style="font-size:0.9rem; color:#7C3AED; margin-top:0.3rem;">
        ⚡ Real-time comparison across Zepto · Blinkit · Instamart · BigBasket
    </p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# Search Bar
# ──────────────────────────────────────────────────
col_search, col_btn = st.columns([5, 1])
with col_search:
    search_query = st.text_input(
        "main_search",
        placeholder="🔍  Search for any grocery product…  e.g. 'Amul Milk', 'Maggi', 'Basmati Rice'",
        label_visibility="collapsed",
        key="main_home_search",
    )
with col_btn:
    search_btn = st.button("Search →", use_container_width=True, type="primary")

if search_btn and search_query.strip():
    # Pass query to product search page via session state
    st.session_state["home_search"] = search_query
    st.switch_page("pages/2_🔍_Product_Search.py")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# Platform showcase
# ──────────────────────────────────────────────────
st.markdown("##### 🏪 Compare Across India's Top Quick-Commerce Platforms")
plat_cols = st.columns(4)
for i, (key, cfg) in enumerate(PLATFORM_CONFIG.items()):
    with plat_cols[i]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{cfg['bg_color']},{cfg['color']}33);
                    border:1px solid {cfg['color']}66; border-radius:16px;
                    padding:1.5rem 1rem; text-align:center; cursor:pointer;
                    transition:transform 0.2s ease;">
            <div style="font-size:2.5rem;">{cfg['emoji']}</div>
            <div style="font-weight:800; color:{cfg['color']}; font-size:1.2rem;
                        margin:0.4rem 0;">{cfg['display']}</div>
            <div style="font-size:0.78rem; color:#9CA3AF;">{cfg['tagline']}</div>
            <div style="margin-top:0.8rem; background:{cfg['color']}22;
                        border-radius:8px; padding:0.3rem 0.6rem;
                        font-size:0.72rem; color:{cfg['color']};">
                Free delivery above ₹{cfg['free_delivery_threshold']}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# Feature Cards
# ──────────────────────────────────────────────────
st.markdown("### ✨ What You Can Do with PricePulse")
feat_cols = st.columns(3)
features = [
    {
        "icon": "🔍",
        "title": "Product Search",
        "desc": "Compare prices for any grocery item across all platforms instantly. "
                "See base price, delivery fee, platform fee, and total landed cost.",
        "link": "pages/2_🔍_Product_Search.py",
        "btn":  "Search Now →",
        "color": "#7C3AED",
    },
    {
        "icon": "🛒",
        "title": "Basket Comparison",
        "desc": "Add multiple items to your basket and compare the total cost. "
                "Our Smart Optimizer tells you whether to buy from one or split orders.",
        "link": "pages/3_🛒_Basket_Comparison.py",
        "btn":  "Build Basket →",
        "color": "#F59E0B",
    },
    {
        "icon": "🤖",
        "title": "AI Assistant",
        "desc": "Chat with our AI to find ingredients for any recipe within your budget. "
                "It suggests the cheapest platform and builds a shopping list for you.",
        "link": "pages/4_🤖_AI_Assistant.py",
        "btn":  "Chat Now →",
        "color": "#10B981",
    },
    {
        "icon": "🔔",
        "title": "Price Alerts",
        "desc": "Set target prices for your favourite items and get notified when "
                "the price drops to your target on any or a specific platform.",
        "link": "pages/5_🔔_Price_Alerts.py",
        "btn":  "Set Alert →",
        "color": "#EF4444",
    },
    {
        "icon": "📊",
        "title": "Savings Dashboard",
        "desc": "Explore platform analytics, price trends, and savings opportunities. "
                "See which platform offers the best value for your shopping patterns.",
        "link": "pages/6_📊_Savings_Dashboard.py",
        "btn":  "View Dashboard →",
        "color": "#8B5CF6",
    },
    {
        "icon": "💡",
        "title": "Smart Recommendations",
        "desc": "Get ML-powered product recommendations based on your searches. "
                "Discover alternatives and similar products at better prices.",
        "link": "pages/2_🔍_Product_Search.py",
        "btn":  "Discover →",
        "color": "#06B6D4",
    },
]

for i, feat in enumerate(features):
    with feat_cols[i % 3]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1E103A,#2D1B4E);
                    border:1px solid {feat['color']}44; border-radius:16px;
                    padding:1.5rem; margin-bottom:1rem; height:100%;">
            <div style="font-size:2.5rem; margin-bottom:0.8rem;">{feat['icon']}</div>
            <div style="font-weight:700; font-size:1.1rem; color:{feat['color']};
                        margin-bottom:0.5rem;">{feat['title']}</div>
            <div style="font-size:0.85rem; color:#9CA3AF; line-height:1.5;">
                {feat['desc']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(feat["btn"], key=f"feat_{i}", use_container_width=True):
            st.switch_page(feat["link"])

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# How It Works
# ──────────────────────────────────────────────────
st.markdown("### 🎯 How PricePulse Works")
step_cols = st.columns(4)
steps = [
    ("1️⃣", "Search", "Enter any grocery product name in the search bar"),
    ("2️⃣", "Compare", "See prices across all platforms with total landed costs"),
    ("3️⃣", "Optimise", "Our AI finds the cheapest option for your full basket"),
    ("4️⃣", "Save", "Save up to 30% on your grocery bill every week"),
]
for col, (num, title, desc) in zip(step_cols, steps):
    with col:
        st.markdown(f"""
        <div style="text-align:center; padding:1.5rem 1rem;">
            <div style="font-size:2.5rem;">{num}</div>
            <div style="font-weight:700; color:#A78BFA; font-size:1rem;
                        margin:0.5rem 0;">{title}</div>
            <div style="font-size:0.82rem; color:#9CA3AF;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# Popular Products Quick-access
# ──────────────────────────────────────────────────
st.markdown("### 🌟 Popular Searches")
popular_terms = [
    "Amul Milk", "Maggi Noodles", "Aashirvaad Atta", "Tata Salt",
    "Parle G", "Nescafe Coffee", "Fortune Oil", "Basmati Rice",
    "Amul Butter", "Good Day Biscuits",
]
pop_cols = st.columns(5)
for i, term in enumerate(popular_terms):
    with pop_cols[i % 5]:
        if st.button(f"🔍 {term}", key=f"pop_{i}", use_container_width=True):
            st.session_state["home_search"] = term
            st.switch_page("pages/2_🔍_Product_Search.py")

# ──────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; color:#374151; font-size:0.82rem;
            padding:2rem 0; border-top:1px solid #1F2937;">
    <div style="margin-bottom:0.5rem;">
        <span style="color:#7C3AED; font-weight:700;">💜 PricePulse</span> &nbsp;—&nbsp;
        Smart Grocery Comparison for India
    </div>
    <div>
        Built with ❤️ using Streamlit &nbsp;|&nbsp;
        Prices updated every hour &nbsp;|&nbsp;
        Data covers 50+ popular products across 4 platforms
    </div>
    <div style="margin-top:0.5rem; color:#6B7280;">
        ⚠️ Prices are indicative and may vary based on your location and platform promotions.
    </div>
</div>
""", unsafe_allow_html=True)
