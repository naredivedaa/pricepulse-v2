"""
PricePulse - User Profile Page
View and edit profile, manage preferences, view saved baskets and history.
"""

import streamlit as st
import json
from utils.helpers import inject_global_css, render_sidebar_logo, PLATFORM_CONFIG, fmt_currency
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in, render_login_form
from utils.db import (
    init_database, get_user_by_id, update_user_profile,
    get_user_search_history, get_user_baskets, get_user_alerts
)


# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="PricePulse – Profile",
    page_icon="👤",
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

st.markdown("## 👤 Profile")

# ── Auth gate ───────────────────────────────────
if not is_logged_in():
    st.info("Please sign in to view your profile.")
    render_login_form()
    st.stop()

session_user = get_current_user()
user_id = session_user["user_id"]
db_user  = get_user_by_id(user_id) or session_user


# ══════════════════════════════════════════════
# Profile tabs
# ══════════════════════════════════════════════
tab_overview, tab_edit, tab_history, tab_baskets, tab_settings = st.tabs([
    "🏠 Overview", "✏️ Edit Profile", "🕐 History", "🧺 Saved Baskets", "⚙️ Settings"
])


# ── Overview Tab ────────────────────────────────
with tab_overview:
    over_col1, over_col2 = st.columns([1, 2])

    with over_col1:
        # Avatar
        initials = (
            "".join(w[0].upper() for w in str(db_user.get("full_name","")).split()[:2])
            or str(db_user.get("username","U"))[0].upper()
        )
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#7C3AED,#9D5FFF);
                    width:100px; height:100px; border-radius:50%;
                    display:flex; align-items:center; justify-content:center;
                    font-size:2.5rem; font-weight:800; color:white;
                    margin:0 auto 1rem auto;">
            {initials}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center;">
            <div style="font-size:1.3rem; font-weight:700; color:#E2E8F0;">
                {db_user.get('full_name') or db_user.get('username','')}
            </div>
            <div style="color:#9CA3AF; font-size:0.85rem;">
                @{db_user.get('username','')}
            </div>
            <div style="color:#9CA3AF; font-size:0.8rem; margin-top:0.3rem;">
                📍 {db_user.get('city','') or 'City not set'}
            </div>
            <div style="margin-top:0.8rem;">
                <span style="background:#2D1B4E; color:#A78BFA;
                             padding:4px 12px; border-radius:8px; font-size:0.8rem;">
                    ✅ Active Member
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with over_col2:
        st.markdown("#### Account Information")

        info_items = [
            ("📧 Email",       db_user.get("email", "—")),
            ("👤 Username",    db_user.get("username", "—")),
            ("📍 City",        db_user.get("city", "Not set")),
            ("📮 Pincode",     db_user.get("pincode", "Not set")),
            ("📅 Member Since", str(db_user.get("created_at",""))[:10]),
            ("🕐 Last Login",  str(db_user.get("last_login",""))[:16]),
        ]
        for label, value in info_items:
            st.markdown(f"""
            <div style="background:#1E103A; border:1px solid #2D1B4E; border-radius:10px;
                        padding:0.6rem 1rem; margin-bottom:0.4rem;
                        display:flex; justify-content:space-between;">
                <span style="color:#9CA3AF; font-size:0.85rem;">{label}</span>
                <span style="color:#E2E8F0; font-size:0.85rem; font-weight:500;">{value}</span>
            </div>
            """, unsafe_allow_html=True)

    # Quick stats
    st.markdown("---")
    st.markdown("#### 📊 Your Stats")
    stat_cols = st.columns(4)
    history = get_user_search_history(user_id, 100)
    baskets_df = get_user_baskets(user_id)
    alerts_df  = get_user_alerts(user_id)

    with stat_cols[0]:
        st.metric("🔍 Searches", len(history))
    with stat_cols[1]:
        st.metric("🧺 Baskets", len(baskets_df))
    with stat_cols[2]:
        st.metric("🔔 Alerts", len(alerts_df))
    with stat_cols[3]:
        st.metric("💰 Saved", "₹0")


# ── Edit Profile Tab ─────────────────────────────
with tab_edit:
    st.markdown("#### ✏️ Edit Your Profile")
    with st.form("edit_profile_form"):
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            new_fullname = st.text_input(
                "Full Name",
                value=db_user.get("full_name", "") or "",
            )
            new_city = st.text_input(
                "City",
                value=db_user.get("city", "") or "",
            )
        with e_col2:
            new_pincode = st.text_input(
                "Pincode",
                value=db_user.get("pincode", "") or "",
            )
            st.text_input(
                "Email",
                value=db_user.get("email", ""),
                disabled=True,
                help="Email cannot be changed.",
            )

        save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if save_btn:
        update_user_profile(user_id, new_fullname, new_city, new_pincode)
        # Update session
        st.session_state["pp_full_name"] = new_fullname
        st.success("✅ Profile updated successfully!")
        st.rerun()


# ── History Tab ──────────────────────────────────
with tab_history:
    st.markdown("#### 🕐 Recent Search History")
    history = get_user_search_history(user_id, 20)

    if not history:
        st.info("No search history yet. Start searching products!")
    else:
        for i, item in enumerate(history):
            st.markdown(f"""
            <div style="background:#1E103A; border:1px solid #2D1B4E; border-radius:10px;
                        padding:0.6rem 1rem; margin-bottom:0.4rem;
                        display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#E2E8F0; font-size:0.9rem;">
                    🔍 {item.get('query','')}
                </span>
                <span style="color:#6B7280; font-size:0.75rem;">
                    {str(item.get('searched_at',''))[:16]}
                </span>
            </div>
            """, unsafe_allow_html=True)


# ── Saved Baskets Tab ────────────────────────────
with tab_baskets:
    st.markdown("#### 🧺 Saved Baskets")
    baskets_df = get_user_baskets(user_id)

    if baskets_df.empty:
        st.info("No saved baskets yet. Build one in the Basket Comparison page!")
    else:
        for _, basket in baskets_df.iterrows():
            cheapest_plat = basket.get("cheapest_platform", "")
            cfg = PLATFORM_CONFIG.get(cheapest_plat, {})

            # Parse items
            try:
                items = json.loads(basket.get("items", "[]"))
                item_names = ", ".join(i.get("product_name","") for i in items[:4])
                if len(items) > 4:
                    item_names += f" +{len(items)-4} more"
            except Exception:
                item_names = "—"

            totals = {
                p: basket.get(f"total_{p}", 0) or 0
                for p in ["zepto", "blinkit", "instamart", "bigbasket"]
            }
            min_total = min((v for v in totals.values() if v > 0), default=0)

            st.markdown(f"""
            <div style="background:#1E103A; border:1px solid #3D2B5E; border-radius:14px;
                        padding:1rem 1.2rem; margin-bottom:0.8rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; color:#E2E8F0; font-size:1rem;">
                            🧺 {basket.get('basket_name','')}
                        </div>
                        <div style="color:#9CA3AF; font-size:0.75rem; margin-top:0.2rem;">
                            {item_names}
                        </div>
                        <div style="color:#6B7280; font-size:0.72rem; margin-top:0.2rem;">
                            Saved: {str(basket.get('created_at',''))[:10]}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#4ADE80; font-weight:700; font-size:1.1rem;">
                            ₹{min_total:.0f}
                        </div>
                        <div style="font-size:0.72rem; color:{cfg.get('color','#A78BFA')};">
                            {cfg.get('emoji','')} {cfg.get('display','')}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── Settings Tab ─────────────────────────────────
with tab_settings:
    st.markdown("#### ⚙️ App Preferences")

    st.markdown("""
    <div style="background:#1A0030; border:1px solid #3D2B5E; border-radius:12px;
                padding:1rem 1.2rem; margin-bottom:1rem;">
        <div style="color:#A78BFA; font-weight:600; margin-bottom:0.5rem;">
            🎨 Display Preferences
        </div>
    </div>
    """, unsafe_allow_html=True)

    default_platform = st.selectbox(
        "Preferred Platform",
        ["zepto", "blinkit", "instamart", "bigbasket"],
        format_func=lambda p: PLATFORM_CONFIG.get(p, {}).get("display", p.title()),
    )
    show_out_of_stock = st.toggle("Show out-of-stock items", value=False)
    notifications_enabled = st.toggle("Enable price drop notifications", value=True)
    show_delivery_fee = st.toggle("Include delivery fee in comparisons", value=True)

    st.markdown("---")
    st.markdown("#### 🔐 Security")

    if st.button("🔑 Change Password (Coming Soon)", disabled=True):
        pass

    st.markdown("---")
    col_save, col_danger = st.columns([1, 1])
    with col_save:
        if st.button("💾 Save Preferences", use_container_width=True):
            st.success("✅ Preferences saved!")

    with col_danger:
        if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
            st.warning(
                "⚠️ This action cannot be undone. "
                "Contact support to permanently delete your account."
            )
