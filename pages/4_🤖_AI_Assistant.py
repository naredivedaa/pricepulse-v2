"""
PricePulse - AI Shopping Assistant Page
Chat interface that understands natural language shopping queries,
builds shopping lists, estimates costs, and recommends platforms.
Includes OpenAI API integration with graceful fallback.
"""

import streamlit as st
import time
import os
from utils.helpers import inject_global_css, render_sidebar_logo, PLATFORM_CONFIG, fmt_currency
from utils.auth import render_sidebar_auth, get_current_user, is_logged_in
from utils.db import init_database
from modules.recommendation_engine import parse_shopping_query


# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="PricePulse – AI Assistant",
    page_icon="🤖",
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

# ── OpenAI config in sidebar ────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 AI Configuration")
openai_key = st.sidebar.text_input(
    "OpenAI API Key (optional)",
    type="password",
    placeholder="sk-...",
    help="Enter your OpenAI API key for GPT-powered responses. "
         "Without it, the built-in AI engine is used.",
)

ai_model = st.sidebar.selectbox(
    "AI Model",
    ["Built-in Engine", "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
    index=0,
)

# ── Chat history state ──────────────────────────
if "ai_chat_history" not in st.session_state:
    st.session_state["ai_chat_history"] = []

chat_history = st.session_state["ai_chat_history"]


# ──────────────────────────────────────────────
# AI Response Functions
# ──────────────────────────────────────────────

def get_openai_response(user_msg: str, api_key: str, model: str) -> str:
    """
    Call the OpenAI Chat Completions API.
    Returns a response string or an error message.
    """
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        system_prompt = """You are PricePulse AI, a smart grocery shopping assistant 
        for India. You help users:
        1. Find ingredients for recipes with budget constraints
        2. Identify cheapest platforms (Zepto, Blinkit, Instamart, BigBasket)
        3. Build optimal shopping lists
        4. Compare grocery prices
        5. Suggest money-saving tips

        Always respond in a friendly, concise manner. 
        Use Indian Rupee (₹) for prices. Keep responses under 200 words.
        Format shopping lists with bullet points."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": m["role"], "content": m["content"]} for m in chat_history[-10:]],
                {"role": "user", "content": user_msg},
            ],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        return None
    except Exception as e:
        return f"OpenAI error: {str(e)}"


def get_builtin_response(user_msg: str) -> dict:
    """
    Use the built-in recommendation engine to parse and respond.
    Returns a dict with response text and structured data.
    """
    result = parse_shopping_query(user_msg)

    intent   = result.get("intent", "generic")
    recipe   = result.get("recipe", "")
    items    = result.get("shopping_list", [])
    cost     = result.get("estimated_cost", 0)
    platform = result.get("cheapest_platform", "")
    plat_dis = result.get("cheapest_platform_display", "")
    budget   = result.get("budget")
    products = result.get("products")

    # Build response message
    if intent == "recipe" and items:
        response = (
            f"🍳 Great choice! Here's what you need for **{recipe}**:\n\n"
            + "\n".join(f"• {item}" for item in items)
            + f"\n\n💰 **Estimated Cost:** {fmt_currency(cost)}"
            + f"\n🏆 **Best Platform:** {plat_dis}"
        )
        if budget:
            if cost <= budget:
                response += f"\n✅ Fits within your budget of ₹{budget:.0f}!"
            else:
                response += f"\n⚠️ Slightly over budget (₹{budget:.0f}). Consider reducing quantities."
    elif products is not None and not products.empty:
        prod_list = products["product_name"].tolist()[:5]
        response = (
            f"🛒 Here are the best matches:\n\n"
            + "\n".join(f"• {p}" for p in prod_list)
            + f"\n\n💰 **Estimated Total:** {fmt_currency(cost)}"
            + f"\n🏆 **Cheapest Platform:** {plat_dis}"
        )
    else:
        # Generic helpful response
        response = _generate_generic_response(user_msg)

    return {"text": response, "data": result}


def _generate_generic_response(query: str) -> str:
    """Fallback response for queries not matched by the engine."""
    q = query.lower()

    if any(w in q for w in ["hello", "hi", "hey", "namaste"]):
        return (
            "👋 Namaste! I'm your PricePulse shopping assistant.\n\n"
            "I can help you:\n"
            "• 🍳 Find ingredients for any recipe with a budget\n"
            "• 💰 Compare prices across Zepto, Blinkit, Instamart & BigBasket\n"
            "• 🛒 Build an optimised shopping basket\n"
            "• 💡 Suggest money-saving tips\n\n"
            "Try asking: _'Find ingredients for pasta under ₹500'_"
        )
    if any(w in q for w in ["cheapest", "cheap", "best price", "lowest"]):
        return (
            "💡 **Platform Price Guide:**\n\n"
            "⚡ **Zepto** – Fastest delivery (8-12 min), good deals\n"
            "🟡 **Blinkit** – Large catalogue, frequent discounts\n"
            "🛒 **Instamart** – Swiggy integration, combo offers\n"
            "🧺 **BigBasket** – Widest range, best for bulk buying\n\n"
            "Search any product on the 🔍 **Product Search** page to compare real-time prices!"
        )
    if any(w in q for w in ["save", "saving", "discount", "offer"]):
        return (
            "💰 **Top Money-Saving Tips:**\n\n"
            "1. 🧺 Consolidate orders on BigBasket for free delivery\n"
            "2. ⚡ Check Zepto for flash deals\n"
            "3. 🔔 Set price alerts for your most-bought items\n"
            "4. 🛒 Use the Basket Optimizer to split orders\n"
            "5. 🎫 Look for platform coupons during sales\n\n"
            "_You can save ₹50-200 per week with smart shopping!_ 📈"
        )
    if any(w in q for w in ["delivery", "time", "fast", "quick"]):
        return (
            "🚀 **Delivery Speed Comparison:**\n\n"
            "⚡ Zepto: 8–12 minutes\n"
            "🟡 Blinkit: 10–15 minutes\n"
            "🛒 Instamart: 15–20 minutes\n"
            "🧺 BigBasket: 60–90 minutes\n\n"
            "_For urgent needs, Zepto & Blinkit are your best bets!_"
        )
    return (
        f"🤔 I can help you with: recipe ingredients, price comparisons, and savings tips.\n\n"
        f"Try asking:\n"
        f"• _'Ingredients for biryani under ₹800'_\n"
        f"• _'Find cheapest milk'_\n"
        f"• _'How to save on groceries?'_"
    )


# ── Page Header ────────────────────────────────
st.markdown("## 🤖 AI Shopping Assistant")
st.markdown("""
<div style="background:linear-gradient(135deg,#1E0A3C,#2D1463);
            border:1px solid #3D2B5E; border-radius:16px; padding:1rem 1.5rem;
            margin-bottom:1.5rem;">
    <p style="margin:0; color:#C4B5FD; font-size:0.95rem;">
        💬 Chat with your AI grocery assistant. Ask for recipes, price comparisons,
        shopping lists, or savings tips. I understand natural language!
    </p>
</div>
""", unsafe_allow_html=True)

# ── Example prompts ─────────────────────────────
st.markdown("##### 💡 Try these examples:")
example_cols = st.columns(4)
examples = [
    "Find ingredients for pasta under ₹500",
    "Cheapest milk on any platform?",
    "Build a breakfast shopping list",
    "How can I save on weekly groceries?",
]
for col, example in zip(example_cols, examples):
    with col:
        if st.button(f"💬 {example[:28]}…" if len(example) > 28 else f"💬 {example}",
                     use_container_width=True, key=f"ex_{example[:10]}"):
            st.session_state["ai_input"] = example

# ── Chat history display ────────────────────────
st.markdown("---")
chat_container = st.container()
with chat_container:
    if not chat_history:
        st.markdown("""
        <div style="text-align:center; padding:3rem; color:#6B7280;">
            <div style="font-size:3rem;">🤖</div>
            <p style="color:#9CA3AF; margin-top:0.5rem;">
                Say hello or ask about any product!
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-end; margin:0.5rem 0;">
                    <div class="chat-user">
                        {msg['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # AI message
                has_data = msg.get("has_data", False)
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-start; margin:0.5rem 0;">
                    <div style="margin-right:8px; font-size:1.5rem;">🤖</div>
                    <div class="chat-ai">
                        {msg['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Structured data card if available
                if has_data and "structured_data" in msg:
                    data = msg["structured_data"]
                    products_df = data.get("products")
                    cost = data.get("estimated_cost", 0)
                    plat = data.get("cheapest_platform_display", "")
                    items = data.get("shopping_list", [])

                    if cost > 0:
                        with st.expander("📊 View Price Details", expanded=False):
                            kpi1, kpi2, kpi3 = st.columns(3)
                            with kpi1:
                                st.metric("Estimated Cost", fmt_currency(cost))
                            with kpi2:
                                st.metric("Cheapest Platform", plat or "N/A")
                            with kpi3:
                                st.metric("Items Found", len(items))

                            if products_df is not None and not products_df.empty:
                                st.dataframe(
                                    products_df[["product_name", "brand", "category"]],
                                    use_container_width=True,
                                    hide_index=True,
                                )

                            # Add all to basket
                            if products_df is not None and not products_df.empty:
                                if st.button("🛒 Add All to Basket",
                                             key=f"add_all_{len(chat_history)}"):
                                    if "pp_basket" not in st.session_state:
                                        st.session_state["pp_basket"] = []
                                    for _, prod in products_df.iterrows():
                                        existing = [
                                            b for b in st.session_state["pp_basket"]
                                            if b["product_id"] == prod.get("product_id")
                                        ]
                                        if not existing:
                                            st.session_state["pp_basket"].append({
                                                "product_id": prod.get("product_id"),
                                                "product_name": prod.get("product_name"),
                                                "quantity": 1,
                                            })
                                    st.success("✅ Added to basket! Go to Basket Comparison to compare.")

# ── Input area ──────────────────────────────────
st.markdown("---")
input_col, send_col = st.columns([5, 1])
with input_col:
    user_input = st.text_input(
        "Chat input",
        value=st.session_state.get("ai_input", ""),
        placeholder="Type your message… e.g. 'Find ingredients for biryani under ₹800'",
        label_visibility="collapsed",
        key="ai_chat_input",
    )
with send_col:
    send_btn = st.button("Send →", use_container_width=True)

# Clear the pre-filled example after use
if "ai_input" in st.session_state and user_input:
    del st.session_state["ai_input"]

# ── Clear chat ──────────────────────────────────
if st.button("🗑️ Clear Chat", help="Clear conversation history"):
    st.session_state["ai_chat_history"] = []
    st.rerun()

# ── Process message ─────────────────────────────
if send_btn and user_input.strip():
    # Add user message
    chat_history.append({"role": "user", "content": user_input.strip()})

    with st.spinner("🤖 Thinking…"):
        time.sleep(0.5)  # Simulates thinking

        structured_data = None

        # Try OpenAI first if key provided and not built-in
        if openai_key and ai_model != "Built-in Engine":
            ai_response = get_openai_response(user_input, openai_key, ai_model)
            if ai_response and not ai_response.startswith("OpenAI error"):
                response_text = ai_response
            else:
                # Fallback to built-in
                result = get_builtin_response(user_input)
                response_text = result["text"]
                structured_data = result["data"]
        else:
            # Built-in engine
            result = get_builtin_response(user_input)
            response_text = result["text"]
            structured_data = result["data"]

    # Add AI response
    ai_msg = {
        "role": "assistant",
        "content": response_text,
        "has_data": structured_data is not None,
    }
    if structured_data:
        ai_msg["structured_data"] = structured_data

    chat_history.append(ai_msg)
    st.rerun()
