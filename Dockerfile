# ─────────────────────────────────────────────────────
# PricePulse - Docker Configuration
# Build: docker build -t pricepulse .
# Run:   docker run -p 8501:8501 pricepulse
# ─────────────────────────────────────────────────────

FROM python:3.11-slim

# ── Metadata ──────────────────────────────────────────
LABEL maintainer="PricePulse Team <hello@pricepulse.app>"
LABEL version="1.0.0"
LABEL description="PricePulse - Smart Grocery Price Comparison Platform"

# ── Environment variables ──────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

# ── System dependencies ────────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application code ──────────────────────────────
COPY . .

# ── Create necessary directories ──────────────────────
RUN mkdir -p database assets/icons

# ── Streamlit configuration ────────────────────────────
RUN mkdir -p .streamlit
COPY .streamlit/config.toml .streamlit/config.toml 2>/dev/null || \
    echo '[server]\nheadless = true\naddress = "0.0.0.0"\nport = 8501\n\n[theme]\nbase = "dark"\nprimaryColor = "#7C3AED"\nbackgroundColor = "#0F0F1A"\nsecondaryBackgroundColor = "#1E103A"\ntextColor = "#E2E8F0"' > .streamlit/config.toml

# ── Expose port ────────────────────────────────────────
EXPOSE 8501

# ── Health check ──────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Startup command ────────────────────────────────────
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
