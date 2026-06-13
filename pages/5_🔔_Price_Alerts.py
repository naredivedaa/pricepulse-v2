"""
PricePulse - Price Alerts Page
Create, manage, and monitor price drop alerts for grocery products.
"""

import streamlit as st
import pandas as pd
from utils.helpers import inject_global_css, render_sidebar_logo, PLATFORM_CONFIG, fmt_currency
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in, require_login
from utils.db import init_database
from modules.search_engine import search_products
from modules.alerts import (
    create_alert, check_alerts, get_alerts_with_current_prices, remove_alert
)


# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Alerts",
    page_icon="🔔",
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

# ── Auth gate ───────────────────────────────────
st.markdown("## 🔔 Price Alerts")
st.markdown("Get notified when your favourite products drop to your target price.")

if not is_logged_in():
    st.warning("👤 Please sign in to create and manage price alerts.")
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#6B7280;">
        <div style="font-size:4rem;">🔔</div>
        <h3 style="color:#9CA3AF;">Sign in to track prices</h3>
        <p>Create alerts and we'll notify you when prices drop!</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

user = get_current_user()
user_id = user["user_id"]

# ── Check triggered alerts ──────────────────────
triggered = check_alerts(user_id)
if triggered:
    st.markdown("### 🎉 Price Drop Notifications!")
    for t in triggered:
        cfg = PLATFORM_CONFIG.get(t["platform"], {})
        st.success(
            f"🔔 **{t['product_name']}** is now "
            f"**{fmt_currency(t['current_price'])}** on "
            f"{cfg.get('emoji','')} **{t['platform_display']}** "
            f"(your target: {fmt_currency(t['target_price'])})"
        )
    st.markdown("---")

# ── Tabs: Create | Manage ───────────────────────
tab_create, tab_manage = st.tabs(["➕ Create New Alert", "📋 My Alerts"])

# ══════════════════════════════════════════════
# CREATE ALERT TAB
# ══════════════════════════════════════════════
with tab_create:
    st.markdown("### 🎯 Set a Price Alert")
    st.markdown(
        "Search for a product, set your target price, and we'll monitor it for you."
    )

    create_col1, create_col2 = st.columns([3, 2])

    with create_col1:
        # ── Search product ──────────────────────
        alert_search = st.text_input(
            "Search Product",
            placeholder="e.g. Amul Milk, Maggi, Nescafe…",
            key="alert_search_q",
        )

        if alert_search:
            with st.spinner("Searching…"):
                search_res = search_products(alert_search, limit=8)

            if search_res.empty:
                st.warning("No products found.")
            else:
                st.markdown(f"##### Found {len(search_res)} products:")
                selected_product = st.radio(
                    "Select a product",
                    options=search_res["product_id"].tolist(),
                    format_func=lambda pid: (
                        search_res.loc[search_res["product_id"] == pid, "product_name"].values[0]
                        + " — "
                        + search_res.loc[search_res["product_id"] == pid, "brand"].values[0]
                        + " (" + search_res.loc[search_res["product_id"] == pid, "unit"].values[0] + ")"
                    ),
                    key="alert_product_radio",
                )

                # Show current prices for selected product
                if selected_product:
                    from modules.comparison_engine import get_product_comparison
                    comp_df = get_product_comparison(selected_product)

                    if not comp_df.empty:
                        st.markdown("##### Current Prices:")
                        for _, pr in comp_df.iterrows():
                            if pr.get("in_stock", 0) == 0:
                                continue
                            cfg = PLATFORM_CONFIG.get(pr["platform"], {})
                            total = float(pr.get("price", 0)) + float(pr.get("delivery_fee", 0))
                            st.markdown(
                                f"{cfg.get('emoji','')} **{cfg.get('display','')}**: "
                                f"₹{total:.0f}"
                            )

        with create_col2:
            st.markdown("##### ⚙️ Alert Settings")

            if alert_search and not search_res.empty and selected_product:
                prod_row = search_res[search_res["product_id"] == selected_product].iloc[0]
                st.info(f"Product: **{prod_row.get('product_name','')}**")

                # Get current best price
                best_price = float(prod_row.get("best_price") or prod_row.get("min_price") or 100)

                target_price = st.number_input(
                    "Target Price (₹)",
                    min_value=1.0,
                    max_value=float(best_price) * 1.2,
                    value=round(float(best_price) * 0.85, 0),
                    step=1.0,
                    help="You'll be alerted when price drops to or below this value.",
                )

                platform_opts = ["any", "zepto", "blinkit", "instamart", "bigbasket"]
                alert_platform = st.selectbox(
                    "Monitor Platform",
                    platform_opts,
                    format_func=lambda p: "Any Platform" if p == "any"
                        else f"{PLATFORM_CONFIG.get(p,{}).get('emoji','')} "
                             f"{PLATFORM_CONFIG.get(p,{}).get('display','')}",
                )

                # Preview
                savings_preview = best_price - target_price
                if savings_preview > 0:
                    st.success(
                        f"💰 You'll save **{fmt_currency(savings_preview)}** "
                        f"({savings_preview/best_price*100:.0f}%) vs current price!"
                    )

                if st.button("🔔 Create Alert", use_container_width=True, type="primary"):
                    result = create_alert(
                        user_id=user_id,
                        product_id=selected_product,
                        product_name=prod_row.get("product_name", ""),
                        target_price=target_price,
                        platform=alert_platform,
                    )
                    st.success(result["message"])
                    st.rerun()
            else:
                st.markdown("""
                <div style="color:#6B7280; text-align:center; padding:2rem 0;">
                    <div style="font-size:2.5rem;">👈</div>
                    <p>Search and select a product first</p>
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# MANAGE ALERTS TAB
# ══════════════════════════════════════════════
with tab_manage:
    st.markdown("### 📋 My Active Alerts")

    alerts_df = get_alerts_with_current_prices(user_id)

    if alerts_df.empty:
        st.markdown("""
        <div style="text-align:center; padding:3rem; color:#6B7280;">
            <div style="font-size:4rem;">🔔</div>
            <h3 style="color:#9CA3AF;">No active alerts</h3>
            <p>Create alerts in the previous tab to track price drops!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # KPI row
        kpi1, kpi2, kpi3 = st.columns(3)
        triggered_count = alerts_df[alerts_df["status"].str.contains("Triggered")].shape[0]
        watching_count  = alerts_df[alerts_df["status"].str.contains("Watching")].shape[0]
        avg_target = alerts_df["target_price"].mean()

        with kpi1:
            st.metric("Total Alerts", len(alerts_df))
        with kpi2:
            st.metric("🎯 Triggered", triggered_count)
        with kpi3:
            st.metric("⏳ Watching", watching_count)

        st.markdown("---")

        for _, alert in alerts_df.iterrows():
            alert_id = int(alert.get("alert_id", 0))
            prod_name = alert.get("product_name", "Unknown")
            target    = float(alert.get("target_price", 0))
            current   = alert.get("current_best_price")
            status    = alert.get("status", "")
            platform  = alert.get("platform", "")
            plat_dis  = alert.get("platform_display", "")
            price_diff = alert.get("price_difference")

            is_triggered = "Triggered" in str(status)
            card_border = "2px solid #4ADE80" if is_triggered else "1px solid #3D2B5E"
            card_bg = "#0D2218" if is_triggered else "#1E103A"

            col_info, col_action = st.columns([4, 1])
            with col_info:
                pct_to_go = ""
                if current is not None and price_diff is not None:
                    if float(price_diff) > 0:
                        pct = abs(float(price_diff)) / float(target) * 100
                        pct_to_go = f" (₹{abs(float(price_diff)):.0f} to go)"

                st.markdown(f"""
                <div style="background:{card_bg}; border:{card_border};
                            border-radius:14px; padding:1rem 1.2rem; margin-bottom:0.6rem;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div style="font-weight:700; color:#E2E8F0; font-size:1rem;">
                                🛍️ {prod_name}
                            </div>
                            <div style="color:#9CA3AF; font-size:0.8rem; margin-top:0.3rem;">
                                Target: <b style="color:#A78BFA;">₹{target:.0f}</b>
                                &nbsp;|&nbsp;
                                Current: <b style="color:#E2E8F0;">
                                    {'₹' + f"{float(current):.0f}" if current else 'N/A'}
                                </b>
                                {pct_to_go}
                            </div>
                            <div style="font-size:0.75rem; color:#9CA3AF; margin-top:0.2rem;">
                                Platform: {plat_dis or 'Any'} &nbsp;|&nbsp;
                                Created: {str(alert.get('created_at',''))[:10]}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <span style="background:{'#16a34a' if is_triggered else '#374151'};
                                         color:white; padding:4px 10px; border-radius:8px;
                                         font-size:0.8rem; font-weight:600;">
                                {status}
                            </span>
                        </div>
                    </div>
                    {"<div style='margin-top:0.5rem;'><div style='background:#4ADE8033; border-radius:4px; height:6px; width:100%;'><div style='background:#4ADE80; height:6px; border-radius:4px; width:100%;'></div></div></div>" if is_triggered else ""}
                </div>
                """, unsafe_allow_html=True)

            with col_action:
                if st.button("🗑️", key=f"del_alert_{alert_id}", help="Delete Alert"):
                    remove_alert(alert_id)
                    st.success("Alert deleted.")
                    st.rerun()

        # Export option
        st.markdown("---")
        if st.button("📥 Export Alerts as CSV"):
            csv = alerts_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                file_name="pricepulse_alerts.csv",
                mime="text/csv",
            )
