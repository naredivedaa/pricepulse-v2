# 💜 PricePulse — Smart Grocery Price Comparison Platform

> Compare prices across **Zepto**, **Blinkit**, **Instamart**, and **BigBasket** — instantly.

![PricePulse Banner](https://via.placeholder.com/1200x300/1E103A/A78BFA?text=PricePulse+%7C+Smart+Grocery+Price+Comparison)

---

## 🌟 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Product Search** | Full-text + fuzzy search across 50+ products |
| 💰 **Price Comparison** | Side-by-side price comparison with total landed cost |
| 🛒 **Basket Comparison** | Compare full basket costs across all platforms |
| 🤖 **AI Assistant** | Natural language shopping queries with OpenAI integration |
| 🔔 **Price Alerts** | Set target prices and get notified on drops |
| 📊 **Savings Dashboard** | Analytics, trends, and market-share charts |
| 👤 **User Profiles** | Personalised experience with saved history |
| 💡 **Smart Optimizer** | Single-platform vs. split-basket recommendations |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/pricepulse.git
cd pricepulse

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open at **http://localhost:8501** 🎉

### Demo Login
| Field    | Value            |
|----------|------------------|
| Username | `rahul_sharma`   |
| Password | `password123`    |

---

## 📁 Project Structure

```
pricepulse/
├── app.py                      # ← Main entry point
│
├── pages/                      # Streamlit multi-page app pages
│   ├── 1_🏠_Home.py
│   ├── 2_🔍_Product_Search.py
│   ├── 3_🛒_Basket_Comparison.py
│   ├── 4_🤖_AI_Assistant.py
│   ├── 5_🔔_Price_Alerts.py
│   ├── 6_📊_Savings_Dashboard.py
│   └── 7_👤_Profile.py
│
├── modules/                    # Core business logic
│   ├── search_engine.py        # Full-text + fuzzy product search
│   ├── comparison_engine.py    # Price comparison & chart builders
│   ├── basket_optimizer.py     # Multi-platform basket optimisation
│   ├── recommendation_engine.py # ML-based recommendations (TF-IDF)
│   ├── alerts.py               # Price alert management
│   └── analytics.py            # Dashboard KPIs & chart builders
│
├── utils/                      # Shared utilities
│   ├── db.py                   # SQLite database layer (CRUD)
│   ├── helpers.py              # UI helpers, CSS, formatting
│   └── auth.py                 # Authentication & session management
│
├── data/                       # Sample datasets
│   ├── products.csv            # 50 products with metadata
│   ├── prices.csv              # 200 price records (50 products × 4 platforms)
│   └── users.csv               # 5 demo user accounts
│
├── database/                   # Auto-generated SQLite database
│   └── pricepulse.db           # Created on first run
│
├── assets/                     # Static assets
│   ├── logo.png
│   └── icons/
│
├── .streamlit/
│   └── config.toml             # Dark theme configuration
│
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

---

## 🗄️ Database Schema

```sql
-- Core tables
users              -- User accounts with hashed passwords
products           -- Product catalogue (50+ items)
platform_prices    -- Per-platform pricing with all fees
search_history     -- User search logs
price_alerts       -- Target price monitoring
saved_baskets      -- Saved basket comparisons
analytics          -- Savings event tracking
trending_searches  -- Aggregated search popularity
```

The SQLite database is **auto-created and seeded** on first run — no setup required.

---

## 🐳 Docker Deployment

```bash
# Build image
docker build -t pricepulse .

# Run container
docker run -d -p 8501:8501 --name pricepulse pricepulse

# With custom port
docker run -d -p 3000:8501 pricepulse

# View logs
docker logs -f pricepulse

# Stop container
docker stop pricepulse
```

Access at **http://localhost:8501**

---

## ☁️ Streamlit Cloud Deployment

1. **Fork** this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"**
4. Select your forked repository
5. Set **Main file path** to `app.py`
6. Click **"Deploy!"**

### Optional: OpenAI API Key
To enable the AI Assistant with full GPT capabilities:
1. In Streamlit Cloud, go to **App settings → Secrets**
2. Add:
   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   ```

---

## 🔑 OpenAI Integration

The AI Assistant works in two modes:

| Mode | Description |
|------|-------------|
| **Built-in** (default) | Pattern-matching engine, works without API key |
| **GPT-3.5/4** | Full LLM responses, requires OpenAI API key |

To enable GPT mode:
1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. Enter it in the AI Assistant page sidebar

---

## 🧪 Sample Data

| Platform | Products | Avg Price | Delivery Fee |
|----------|----------|-----------|--------------|
| Zepto    | 50       | ₹142      | ₹0 (free above ₹149) |
| Blinkit  | 50       | ₹147      | ₹3 flat     |
| Instamart | 50      | ₹135      | ₹25          |
| BigBasket | 50      | ₹132      | ₹40          |

Includes 50 real Indian grocery brands:
Amul, Maggi, Aashirvaad, Tata, Parle, Britannia, Nescafe, Fortune, Bru, Daawat, and more.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit 1.32+ |
| Backend | Python 3.11 |
| Database | SQLite 3 |
| Data Processing | Pandas, NumPy |
| Visualisation | Plotly |
| Machine Learning | Scikit-learn (TF-IDF, Cosine Similarity) |
| AI | OpenAI GPT-3.5/4 (optional) |
| Auth | hashlib SHA-256 |
| Deployment | Streamlit Cloud, Docker |

---

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Acknowledgements

- [Streamlit](https://streamlit.io) — Amazing Python web framework
- [Plotly](https://plotly.com) — Beautiful interactive charts
- [Scikit-learn](https://scikit-learn.org) — ML toolkit
- Indian grocery brands for inspiration

---

<div align="center">
Made with 💜 for smart Indian grocery shoppers
</div>
