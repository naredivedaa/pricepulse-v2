"""
PricePulse - Basket Comparison Page
Add multiple products, compare total basket costs across platforms,
and use the Smart Basket Optimizer to find the best buying strategy.
"""

import streamlit as st
import pandas as pd
import json
from utils.helpers import (
    inject_global_css, render_sidebar_logo, PLATFORM_CONFIG,
    fmt_currency, get_category_icon, PLATFORM_ORDER
)
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in
from utils.db import init_database, save_basket
from modules.search_engine import search_products
from modules.basket_optimizer import (
    compute_basket_totals, optimize_basket,
    build_basket_comparison_chart, build_split_savings_chart, build_item_heatmap
)


# ── Page config ─────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Basket",
    page_icon="🛒",
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

# ── Session basket ──────────────────────────────
if "pp_basket" not in st.session_state:
    st.session_state["pp_basket"] = []

basket: list = st.session_state["pp_basket"]

# ── Header ──────────────────────────────────────
st.markdown("## 🛒 Basket Comparison")
st.markdown("Build your shopping basket and find the cheapest way to buy everything.")

main_col, basket_col = st.columns([3, 1])

# ── Right: Basket Panel ─────────────────────────
with basket_col:
    st.markdown(f"### 🧺 My Basket ({len(basket)} items)")

    if basket:
        for i, item in enumerate(basket):
            b_col1, b_col2, b_col3 = st.columns([3, 1, 1])
            with b_col1:
                st.markdown(
                    f"<div style='color:#E2E8F0; font-size:0.85rem;'>"
                    f"{get_category_icon('')} {item['product_name'][:22]}</div>",
                    unsafe_allow_html=True,
                )
            with b_col2:
                new_qty = st.number_input(
                    "Qty",
                    min_value=1, max_value=20,
                    value=item.get("quantity", 1),
                    key=f"qty_{i}",
                    label_visibility="collapsed",
                )
                basket[i]["quantity"] = new_qty
            with b_col3:
                if st.button("✕", key=f"rm_{i}", help="Remove item"):
                    basket.pop(i)
                    st.rerun()

        st.markdown("---")
        if st.button("🗑️ Clear Basket", use_container_width=True):
            st.session_state["pp_basket"] = []
            st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center; color:#6B7280; padding:2rem 0;">
            <div style="font-size:3rem;">🛒</div>
            <p>Your basket is empty.<br>Add products from the left.</p>
        </div>
        """, unsafe_allow_html=True)

# ── Left: Add products & Comparison ────────────
with main_col:
    # ── Add product search ─────────────────────
    st.markdown("#### ➕ Add Products to Basket")
    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        add_query = st.text_input(
            "Search to add",
            placeholder="Search product to add…",
            label_visibility="collapsed",
            key="basket_add_q",
        )
    with add_col2:
        add_search = st.button("Find →", use_container_width=True)

    if add_query or add_search:
        user = get_current_user()
        uid  = user.get("user_id") if is_logged_in() else None
        add_results = search_products(add_query, user_id=uid, limit=6)

        if not add_results.empty:
            add_cols = st.columns(3)
            for idx, (_, prod) in enumerate(add_results.iterrows()):
                with add_cols[idx % 3]:
                    best_price = prod.get("best_price") or prod.get("min_price") or 0
                    icon = get_category_icon(str(prod.get("category", "")))
                    st.markdown(f"""
                    <div style="background:#1E103A; border:1px solid #3D2B5E;
                                border-radius:12px; padding:0.8rem; text-align:center;
                                margin-bottom:0.5rem;">
                        <div style="font-size:1.5rem;">{icon}</div>
                        <div style="font-size:0.8rem; font-weight:600; color:#E2E8F0;">
                            {str(prod.get('product_name',''))[:22]}
                        </div>
                        <div style="color:#9CA3AF; font-size:0.72rem;">{prod.get('brand','')}</div>
                        <div style="color:#4ADE80; font-weight:700; font-size:0.9rem;">
                            from ₹{float(best_price):.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("+ Add", key=f"addprod_{prod.get('product_id')}_{idx}",
                                 use_container_width=True):
                        existing = [b for b in basket if b["product_id"] == prod.get("product_id")]
                        if existing:
                            existing[0]["quantity"] += 1
                        else:
                            basket.append({
                                "product_id": prod.get("product_id"),
                                "product_name": prod.get("product_name"),
                                "quantity": 1,
                            })
                        st.success(f"Added {prod.get('product_name','')}!")
                        st.rerun()
        else:
            st.warning("No products found. Try another search.")

    # ── Load demo basket ───────────────────────
    if not basket:
        if st.button("📋 Load Demo Basket (5 items)", use_container_width=False):
            st.session_state["pp_basket"] = [
                {"product_id": "P001", "product_name": "Amul Tazza Milk",      "quantity": 2},
                {"product_id": "P006", "product_name": "Maggi 2-Minute Noodles","quantity": 1},
                {"product_id": "P004", "product_name": "Aashirvaad Atta",       "quantity": 1},
                {"product_id": "P012", "product_name": "Nescafe Classic Coffee", "quantity": 1},
                {"product_id": "P010", "product_name": "Parle-G Biscuits",      "quantity": 2},
            ]
            st.rerun()

    # ── Comparison ─────────────────────────────
    if basket:
        st.markdown("---")
        if st.button("🔍 Compare Prices Across Platforms", use_container_width=True):
            with st.spinner("Computing basket costs…"):
                opt = optimize_basket(basket)
            st.session_state["basket_opt"] = opt

    # ── Results ────────────────────────────────
    if "basket_opt" in st.session_state and basket:
        opt = st.session_state["basket_opt"]
        platform_totals = opt.get("platform_totals", {})
        breakdown_df    = opt.get("item_breakdown", pd.DataFrame())

        if not platform_totals:
            st.error("Could not fetch prices. Please try again.")
        else:
            # ── Platform totals KPIs ───────────────
            st.markdown("### 📊 Platform Cost Comparison")
            kpi_cols = st.columns(4)
            valid_totals = {k: v for k, v in platform_totals.items() if v > 0}
            min_cost = min(valid_totals.values()) if valid_totals else 0

            for i, platform in enumerate(PLATFORM_ORDER):
                total = platform_totals.get(platform, 0)
                cfg   = PLATFORM_CONFIG.get(platform, {})
                with kpi_cols[i]:
                    is_cheap = (total == min_cost and total > 0)
                    border = "2px solid #4ADE80" if is_cheap else "1px solid #3D2B5E"
                    badge  = "✅ CHEAPEST" if is_cheap else ""
                    missing = len(opt.get("missing_items", {}).get(platform, []))

                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#1E103A,#2D1B4E);
                                border:{border}; border-radius:16px; padding:1.2rem;
                                text-align:center;">
                        <div style="font-size:1.8rem;">{cfg.get('emoji','')}</div>
                        <div style="font-weight:700; color:{cfg.get('color','#A78BFA')};">
                            {cfg.get('display','')}
                        </div>
                        <div style="font-size:1.6rem; font-weight:800; color:#E2E8F0;
                                    margin:0.4rem 0;">
                            {"₹" + f"{total:.0f}" if total > 0 else "N/A"}
                        </div>
                        {"<div style='color:#4ADE80; font-size:0.75rem; font-weight:700;'>" + badge + "</div>" if badge else ""}
                        {"<div style='color:#F87171; font-size:0.7rem;'>" + str(missing) + " items unavailable</div>" if missing > 0 else ""}
                    </div>
                    """, unsafe_allow_html=True)

            # ── Main comparison chart ──────────────
            st.plotly_chart(
                build_basket_comparison_chart(platform_totals),
                use_container_width=True, key="basket_main_chart"
            )

            # ── Strategy recommendation ────────────
            st.markdown("### 💡 Smart Basket Optimizer")
            strategy  = opt.get("strategy", "single")
            sing_cost = opt.get("single_cost", 0)
            split_cost = opt.get("split_cost", 0)
            sing_plat = opt.get("single_platform_display", "")
            savings   = opt.get("savings_split_vs_single", 0)

            if strategy == "split":
                st.success(
                    f"✂️ **Split Basket Recommended!** "
                    f"Save **₹{savings:.0f}** by buying from multiple platforms."
                )
                rec_col1, rec_col2 = st.columns([1, 1])
                with rec_col1:
                    st.markdown(f"""
                    <div class="pp-card">
                        <h4 style="color:#9CA3AF;">Option A: Buy All From One</h4>
                        <div style="font-size:1.4rem; font-weight:700; color:#E2E8F0;">
                            ₹{sing_cost:.0f}
                        </div>
                        <div style="color:#9CA3AF; font-size:0.85rem;">
                            Best single platform: <b>{sing_plat}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with rec_col2:
                    st.markdown(f"""
                    <div class="pp-card-highlight">
                        <h4 style="color:#A78BFA;">Option B: Split Basket ⭐</h4>
                        <div style="font-size:1.4rem; font-weight:700; color:#4ADE80;">
                            ₹{split_cost:.0f}
                        </div>
                        <div style="color:#A78BFA; font-size:0.85rem;">
                            Buy each item from cheapest platform
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Split plan detail
                st.markdown("##### 📋 Split Shopping List")
                split_plan = opt.get("split_plan", [])
                if split_plan:
                    plan_rows = []
                    for plan_item in split_plan:
                        cfg = PLATFORM_CONFIG.get(plan_item["platform"], {})
                        plan_rows.append({
                            "Product": plan_item["product_name"],
                            "Qty": plan_item["quantity"],
                            "Platform": f"{cfg.get('emoji','')} {plan_item['platform_display']}",
                            "Cost": f"₹{plan_item['cost']:.0f}",
                        })
                    plan_df = pd.DataFrame(plan_rows)
                    st.dataframe(plan_df, use_container_width=True, hide_index=True)

                st.plotly_chart(
                    build_split_savings_chart(opt),
                    use_container_width=True, key="split_chart"
                )
            else:
                st.info(
                    f"🛍️ **Single Platform Recommended** — Buy everything from "
                    f"**{sing_plat}** for **₹{sing_cost:.0f}**. "
                    f"Splitting would only save ₹{savings:.0f}, not worth the hassle."
                )

            # ── Item breakdown ─────────────────────
            if not breakdown_df.empty:
                st.markdown("### 📋 Item-by-Item Breakdown")
                display_df = breakdown_df.copy()
                for p in PLATFORM_ORDER:
                    if p in display_df.columns:
                        disp_name = PLATFORM_CONFIG.get(p, {}).get("display", p.title())
                        display_df = display_df.rename(columns={p: f"{disp_name} (₹)"})
                        display_df[f"{disp_name} (₹)"] = display_df[f"{disp_name} (₹)"].apply(
                            lambda x: f"₹{x:.0f}" if x is not None and not pd.isna(x) else "N/A"
                        )
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                # Heatmap
                st.plotly_chart(
                    build_item_heatmap(breakdown_df),
                    use_container_width=True, key="heatmap_chart"
                )

            # ── Save basket ─────────────────────────
            st.markdown("---")
            if is_logged_in():
                save_col1, save_col2 = st.columns([3, 1])
                with save_col1:
                    basket_name = st.text_input(
                        "Basket Name",
                        value="My Weekly Grocery",
                        key="basket_name_input",
                    )
                with save_col2:
                    if st.button("💾 Save Basket", use_container_width=True):
                        user = get_current_user()
                        save_basket(
                            user_id=user["user_id"],
                            basket_name=basket_name,
                            items=json.dumps(basket),
                            totals={
                                **platform_totals,
                                "cheapest_platform": opt.get("single_platform", ""),
                                "potential_savings": opt.get("savings_vs_expensive", 0),
                            }
                        )
                        st.success("✅ Basket saved!")
            else:
                st.info("👤 Sign in to save your basket for later.")
