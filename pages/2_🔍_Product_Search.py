"""
PricePulse - Product Search Page
Full product search with price comparison, platform breakdown,
charts, and similar product recommendations.
"""

import streamlit as st
import pandas as pd
from utils.helpers import (
    inject_global_css, render_sidebar_logo, PLATFORM_CONFIG,
    fmt_currency, get_category_icon, render_platform_price_card
)
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in
from utils.db import init_database
from modules.search_engine import search_products, get_all_categories, get_suggestions
from modules.comparison_engine import (
    get_product_comparison, build_price_comparison_chart,
    build_savings_donut, build_delivery_time_chart, get_savings_summary
)
from modules.recommendation_engine import get_similar_products, get_category_recommendations
from modules.alerts import create_alert


# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Search",
    page_icon="🔍",
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

# ── Sidebar filters ────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Filters")
categories = get_all_categories()
cat_filter = st.sidebar.selectbox("Category", categories, index=0)

sort_options = {
    "Most Relevant": "relevance",
    "Price: Low → High": "price_asc",
    "Price: High → Low": "price_desc",
    "Biggest Discount": "discount",
}
sort_by = st.sidebar.selectbox("Sort By", list(sort_options.keys()))

platforms_visible = st.sidebar.multiselect(
    "Platforms to Compare",
    options=["zepto", "blinkit", "instamart", "bigbasket"],
    default=["zepto", "blinkit", "instamart", "bigbasket"],
    format_func=lambda p: PLATFORM_CONFIG.get(p, {}).get("display", p.title()),
)


# ── Page Header ────────────────────────────────
st.markdown("## 🔍 Product Search")
st.markdown("Search for any grocery item to compare prices across all platforms.")

# ── Search Bar ─────────────────────────────────
col_s, col_b = st.columns([5, 1])
with col_s:
    query = st.text_input(
        "Search products",
        value=st.session_state.get("home_search", ""),
        placeholder="e.g. Amul Milk, Maggi, Basmati Rice …",
        label_visibility="collapsed",
        key="product_search_q",
    )
with col_b:
    search_clicked = st.button("🔍 Search", use_container_width=True)

# ── Search execution ────────────────────────────
if query or search_clicked:
    user = get_current_user()
    uid  = user.get("user_id") if is_logged_in() else None

    with st.spinner("🔍 Searching products…"):
        results = search_products(
            query=query,
            user_id=uid,
            category_filter=cat_filter if cat_filter != "All" else None,
        )

    # Sort results
    sort_key = sort_options[sort_by]
    if sort_key == "price_asc" and "best_price" in results.columns:
        results = results.sort_values("best_price", ascending=True)
    elif sort_key == "price_desc" and "best_price" in results.columns:
        results = results.sort_values("best_price", ascending=False)
    elif sort_key == "discount" and "best_discount" in results.columns:
        results = results.sort_values("best_discount", ascending=False)

    if results.empty:
        st.warning(f"😕 No results found for **'{query}'**. Try a different search term.")
        st.info("💡 Try: Amul Milk, Maggi, Tata Salt, Parle G, Nescafe")
    else:
        st.success(f"Found **{len(results)}** products for **'{query}'**")

        # ── Results Grid ──────────────────────────
        for _, prod in results.iterrows():
            with st.expander(
                f"{get_category_icon(str(prod.get('category','')))}  "
                f"**{prod.get('product_name','')}**  —  {prod.get('brand','')}  "
                f"• {prod.get('category','')}  • {prod.get('unit','')}",
                expanded=False,
            ):
                # ── Product detail layout ──────────
                detail_left, detail_right = st.columns([2, 3])

                with detail_left:
                    # Product info card
                    icon = get_category_icon(str(prod.get("category", "")))
                    st.markdown(f"""
                    <div style="background:#1E103A; border:1px solid #3D2B5E;
                                border-radius:16px; padding:1.5rem; text-align:center;">
                        <div style="font-size:4rem;">{icon}</div>
                        <div style="font-size:1.1rem; font-weight:700; color:#E2E8F0;
                                    margin-top:0.8rem;">
                            {prod.get('product_name','')}
                        </div>
                        <div style="color:#9CA3AF; font-size:0.85rem;">
                            {prod.get('brand','')}
                        </div>
                        <div style="margin-top:0.5rem;">
                            <span style="background:#2D1B4E; color:#A78BFA;
                                         padding:3px 10px; border-radius:8px; font-size:0.8rem;">
                                {prod.get('category','')}
                            </span>
                            <span style="background:#2D1B4E; color:#9CA3AF;
                                         padding:3px 10px; border-radius:8px; font-size:0.8rem;
                                         margin-left:6px;">
                                {prod.get('unit','')}
                            </span>
                        </div>
                        <div style="font-size:0.8rem; color:#6B7280; margin-top:0.8rem;">
                            {prod.get('description','')[:100]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Add to basket button
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(
                        f"🛒 Add to Basket",
                        key=f"add_{prod.get('product_id','')}",
                        use_container_width=True,
                    ):
                        if "pp_basket" not in st.session_state:
                            st.session_state["pp_basket"] = []
                        basket = st.session_state["pp_basket"]
                        existing = [b for b in basket if b["product_id"] == prod.get("product_id")]
                        if existing:
                            existing[0]["quantity"] += 1
                            st.success("Quantity updated in basket!")
                        else:
                            basket.append({
                                "product_id": prod.get("product_id"),
                                "product_name": prod.get("product_name"),
                                "quantity": 1,
                            })
                            st.success(f"✅ Added to basket!")

                with detail_right:
                    # Fetch price comparison
                    comp_df = get_product_comparison(prod.get("product_id", ""))

                    # Filter by selected platforms
                    if platforms_visible:
                        comp_df = comp_df[comp_df["platform"].isin(platforms_visible)]

                    if comp_df.empty:
                        st.warning("No price data available.")
                    else:
                        # ── Summary stats ──────────────────
                        summary = get_savings_summary(comp_df)
                        s_col1, s_col2, s_col3 = st.columns(3)
                        with s_col1:
                            st.metric(
                                "Best Price",
                                fmt_currency(summary.get("cheapest_total", 0)),
                                f"{summary.get('best_platform','')}",
                            )
                        with s_col2:
                            st.metric(
                                "Max Savings",
                                fmt_currency(summary.get("max_savings", 0)),
                                f"{summary.get('savings_pct',0):.1f}% off",
                            )
                        with s_col3:
                            st.metric(
                                "Platforms",
                                len(comp_df[comp_df["in_stock"] == 1]),
                                "in stock",
                            )

                        # ── Platform price cards ────────────
                        st.markdown("##### 💰 Price Comparison")
                        for _, price_row in comp_df.iterrows():
                            if price_row.get("platform") not in (platforms_visible or []):
                                continue
                            render_platform_price_card(
                                price_row,
                                is_cheapest=bool(price_row.get("is_cheapest", False))
                            )

                        # ── Charts ─────────────────────────
                        chart_tab1, chart_tab2, chart_tab3 = st.tabs([
                            "📊 Price Breakdown", "🏷️ Discounts", "🕐 Delivery"
                        ])
                        with chart_tab1:
                            st.plotly_chart(
                                build_price_comparison_chart(comp_df),
                                use_container_width=True, key=f"chart1_{prod.get('product_id')}"
                            )
                        with chart_tab2:
                            st.plotly_chart(
                                build_savings_donut(comp_df),
                                use_container_width=True, key=f"chart2_{prod.get('product_id')}"
                            )
                        with chart_tab3:
                            st.plotly_chart(
                                build_delivery_time_chart(comp_df),
                                use_container_width=True, key=f"chart3_{prod.get('product_id')}"
                            )

                        # ── Set Price Alert ─────────────────
                        st.markdown("---")
                        st.markdown("##### 🔔 Set Price Alert")
                        alert_col1, alert_col2 = st.columns([2, 1])
                        with alert_col1:
                            min_price = summary.get("cheapest_total", 50.0)
                            target = st.number_input(
                                "Target Price (₹)",
                                min_value=1.0,
                                max_value=float(min_price) * 1.5,
                                value=float(min_price) * 0.9,
                                step=1.0,
                                key=f"alert_price_{prod.get('product_id')}",
                            )
                        with alert_col2:
                            plat_opts = ["any"] + [
                                p for p in ["zepto","blinkit","instamart","bigbasket"]
                                if p in comp_df["platform"].values
                            ]
                            alert_platform = st.selectbox(
                                "Platform",
                                plat_opts,
                                format_func=lambda p: "Any" if p == "any"
                                    else PLATFORM_CONFIG.get(p, {}).get("display", p),
                                key=f"alert_plat_{prod.get('product_id')}",
                            )

                        if st.button(
                            "🔔 Create Alert",
                            key=f"create_alert_{prod.get('product_id')}",
                        ):
                            if is_logged_in():
                                user = get_current_user()
                                res = create_alert(
                                    user_id=user["user_id"],
                                    product_id=prod.get("product_id"),
                                    product_name=prod.get("product_name"),
                                    target_price=target,
                                    platform=alert_platform,
                                )
                                st.success(res["message"])
                            else:
                                st.warning("👤 Please sign in to create price alerts.")

                # ── Similar Products ───────────────
                similar = get_similar_products(prod.get("product_id", ""), top_n=4)
                if not similar.empty:
                    st.markdown("##### 🔗 Similar Products")
                    sim_cols = st.columns(4)
                    for j, (_, sim_prod) in enumerate(similar.iterrows()):
                        with sim_cols[j % 4]:
                            icon_sim = get_category_icon(str(sim_prod.get("category", "")))
                            best = sim_prod.get("best_total", sim_prod.get("best_price", 0)) or 0
                            st.markdown(f"""
                            <div style="background:#1E103A; border:1px solid #2D1B4E;
                                        border-radius:12px; padding:0.8rem;
                                        text-align:center; font-size:0.8rem;">
                                <div style="font-size:1.8rem;">{icon_sim}</div>
                                <div style="color:#E2E8F0; font-weight:600; margin:0.3rem 0;">
                                    {str(sim_prod.get('product_name',''))[:20]}
                                </div>
                                <div style="color:#4ADE80; font-weight:700;">
                                    ₹{float(best):.0f}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

else:
    # ── Default state ──────────────────────────
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#6B7280;">
        <div style="font-size:4rem;">🔍</div>
        <h3 style="color:#9CA3AF;">Enter a product name to start comparing</h3>
        <p>Try searching for: <b>Amul Milk</b>, <b>Maggi</b>, <b>Tata Salt</b>,
           <b>Basmati Rice</b>, <b>Nescafe Coffee</b></p>
    </div>
    """, unsafe_allow_html=True)
