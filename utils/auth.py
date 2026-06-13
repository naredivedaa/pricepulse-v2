"""
PricePulse - Authentication Module
Handles login, signup, session state management and logout.
"""

import streamlit as st
from utils.db import authenticate_user, create_user, get_user_by_id


# ──────────────────────────────────────────────
# Session State Keys
# ──────────────────────────────────────────────
SESSION_KEYS = {
    "authenticated": "pp_authenticated",
    "user_id": "pp_user_id",
    "username": "pp_username",
    "full_name": "pp_full_name",
    "email": "pp_email",
    "basket": "pp_basket",
}


def is_logged_in() -> bool:
    """Return True if a user session is active."""
    return st.session_state.get(SESSION_KEYS["authenticated"], False)


def get_current_user() -> dict:
    """Return the current user's info from session state."""
    if not is_logged_in():
        return {}
    return {
        "user_id": st.session_state.get(SESSION_KEYS["user_id"]),
        "username": st.session_state.get(SESSION_KEYS["username"]),
        "full_name": st.session_state.get(SESSION_KEYS["full_name"], ""),
        "email": st.session_state.get(SESSION_KEYS["email"], ""),
    }


def login_user(user_data: dict):
    """Set session state for an authenticated user."""
    st.session_state[SESSION_KEYS["authenticated"]] = True
    st.session_state[SESSION_KEYS["user_id"]] = user_data["user_id"]
    st.session_state[SESSION_KEYS["username"]] = user_data["username"]
    st.session_state[SESSION_KEYS["full_name"]] = user_data.get("full_name", "")
    st.session_state[SESSION_KEYS["email"]] = user_data.get("email", "")
    # Initialise basket if not set
    if SESSION_KEYS["basket"] not in st.session_state:
        st.session_state[SESSION_KEYS["basket"]] = []


def logout_user():
    """Clear all authentication-related session state keys."""
    for key in SESSION_KEYS.values():
        if key in st.session_state:
            del st.session_state[key]


def render_login_form():
    """Render a full login / signup form and return True on success."""
    st.markdown("""
    <div style="max-width:480px; margin:0 auto;">
        <div style="text-align:center; margin-bottom:2rem;">
            <div style="font-size:3rem;">💜</div>
            <h1 style="color:#A78BFA; font-weight:800; margin:0;">PricePulse</h1>
            <p style="color:#9CA3AF;">Smart Grocery Price Comparison</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔑 Sign In", "✨ Create Account"])

    # ── Login ─────────────────────────────────
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Welcome back!")
            username = st.text_input("Username or Email", placeholder="Enter username or email")
            password = st.text_input("Password", type="password", placeholder="Enter password")

            col_left, col_right = st.columns([1, 1])
            with col_right:
                submitted = st.form_submit_button("Sign In →", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please fill in all fields.")
                return False
            user = authenticate_user(username, password)
            if user:
                login_user(user)
                st.success(f"Welcome back, {user.get('full_name') or user['username']}! 🎉")
                st.rerun()
                return True
            else:
                st.error("❌ Invalid credentials. Please try again.")
                st.caption("💡 Demo: username `rahul_sharma` / password `password123`")
                return False

        # Demo credentials hint
        st.info("🧪 **Demo Login** — Username: `rahul_sharma` | Password: `password123`")

    # ── Signup ────────────────────────────────
    with tab_signup:
        with st.form("signup_form", clear_on_submit=True):
            st.markdown("#### Join PricePulse")
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", placeholder="cooluser123")
                new_password = st.text_input("Password*", type="password", placeholder="Min 6 chars")
                new_city = st.text_input("City", placeholder="Mumbai")
            with col2:
                new_email = st.text_input("Email*", placeholder="you@email.com")
                new_fullname = st.text_input("Full Name", placeholder="Your Name")
                confirm_password = st.text_input("Confirm Password*", type="password")

            terms = st.checkbox("I agree to the Terms of Service")
            submitted_signup = st.form_submit_button("Create Account 🚀", use_container_width=True)

        if submitted_signup:
            # Validate
            errors = []
            if not new_username or not new_email or not new_password:
                errors.append("Username, email and password are required.")
            if new_password != confirm_password:
                errors.append("Passwords do not match.")
            if len(new_password) < 6:
                errors.append("Password must be at least 6 characters.")
            if not terms:
                errors.append("You must accept the Terms of Service.")

            if errors:
                for err in errors:
                    st.error(err)
                return False

            try:
                user = create_user(
                    username=new_username,
                    email=new_email,
                    password=new_password,
                    full_name=new_fullname,
                    city=new_city,
                )
                login_user(user)
                st.success("🎉 Account created! Welcome to PricePulse!")
                st.rerun()
                return True
            except ValueError as exc:
                st.error(f"❌ {exc}")
                return False

    return False


def require_login(guest_allowed: bool = True) -> bool:
    """
    Check if the user is logged in.
    If guest_allowed=True, show a gentle prompt but don't block.
    If guest_allowed=False, show the login form and stop rendering.
    Returns True if authenticated.
    """
    if is_logged_in():
        return True

    if not guest_allowed:
        render_login_form()
        st.stop()

    return False


def render_sidebar_auth():
    """Render login status and logout button in the sidebar."""
    if is_logged_in():
        user = get_current_user()
        name = user.get("full_name") or user.get("username", "User")
        st.sidebar.markdown(f"""
        <div style="background:linear-gradient(135deg,#1E103A,#2D1B4E);
                    border:1px solid #3D2B5E; border-radius:12px;
                    padding:0.8rem 1rem; margin-bottom:1rem;">
            <div style="font-size:0.8rem; color:#9CA3AF;">Logged in as</div>
            <div style="font-weight:700; color:#A78BFA;">👤 {name}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.sidebar.button("🚪 Sign Out", use_container_width=True):
            logout_user()
            st.rerun()
    else:
        st.sidebar.info("👤 Not logged in\n\nSign in to save alerts & history.")
