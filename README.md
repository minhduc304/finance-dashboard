# Finance Dashboard

A comprehensive personal finance dashboard that integrates multiple data sources to provide real-time portfolio tracking, market analysis, sentiment insights, and technical indicators for informed investment decisions.

![Status](https://img.shields.io/badge/status-active-success)
![Phase](https://img.shields.io/badge/phase-3%20complete-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![React](https://img.shields.io/badge/react-18-blue)

## ✨ Key Features

- **Real-Time Portfolio Tracking** - Automated Wealthsimple integration with auto-sync every 5 minutes
- **Multi-Source Market Data** - Aggregated data from yfinance and Alpha Vantage
- **Social Sentiment Analysis** - 1,944 Reddit posts/day with 87.5% accuracy
- **Technical Indicators** - only 8 indicators implemented for now.
- **Insider Trading Tracking** - Monitor insider buy/sell activity from OpenInsider
- **⚡ Redis API Caching** - 60-70% cache hit rate with 50-90% faster response times
- **News Aggregation** - Sentiment-analyzed news from multiple sources
- **Automated Data Collection** - Celery-based background tasks for continuous updates

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  - Dashboard Views  - Charts  - Screening Tools             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend (Python)                   │
│  - API Endpoints  - Business Logic  - Redis Cache           │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
│ PostgreSQL   │  │   Redis    │  │   Celery    │
│  Database    │  │   Cache    │  │   Workers   │
└──────────────┘  └────────────┘  └──────┬──────┘
                                          │
                         ┌────────────────┴─────────────────┐
                         │                                  │
                  ┌──────▼─────────┐                ┌───────▼────────┐
                  │ Data Collectors|                │  External APIs │
                  │ - Reddit       |                │ - Wealthsimple │
                  │ - yfinance     |                │ - Alpha Vantage│
                  │ - OpenInsider  |                │ - Reddit API   │
                  └────────────────┘────────────────┴────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **Language:** Python 3.12
- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 15+ with SQLAlchemy 2.0+ ORM
- **Cache:** Redis 7.0+ with custom decorator
- **Task Queue:** Celery 5.3+ with Beat scheduler
- **Data Sources:** yfinance, Alpha Vantage, Reddit API (PRAW)
- **Sentiment Analysis:** VADER, TextBlob, NLTK

### Frontend
- **Framework:** React 18+ with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **Charts:** Recharts
- **HTTP Client:** Axios

### Infrastructure
- **Containerization:** Docker & Docker Compose
- **Services:** PostgreSQL, Redis, FastAPI, React
- **Workers:** 8 concurrent Celery workers

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd finance-dashboard
```

2. **Start infrastructure:**
```bash
docker-compose up -d
```

3. **Setup backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Initialize database:**
```bash
python scripts/init_db.py
python scripts/create_validation_table.py
```

5. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys:
# - ALPHA_VANTAGE_API_KEY
# - REDDIT_CLIENT_ID & REDDIT_CLIENT_SECRET
# - WEALTHSIMPLE_EMAIL & WEALTHSIMPLE_PASSWORD
```

6. **Start backend services:**
```bash
# Terminal 1: API Server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery Worker
celery -A app.core.celery_app worker --loglevel=info

# Terminal 3: Celery Beat Scheduler
celery -A app.core.celery_app beat --loglevel=info
```

7. **Start frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Access Points
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

## 📊 Database Schema

The application uses a database schema with **25+ tables** across **6 domains**:

1. **Portfolio Management** - portfolios, holdings, transactions, performance_history, watchlist, alerts
2. **Market Data (yfinance)** - stock_info, stock_prices, stock_news, earnings, financials, dividend_history, stock_splits, analyst_ratings
3. **Social Sentiment (Reddit)** - reddit_posts, reddit_comments, stock_sentiment, sentiment_validation_samples
4. **Insider Trading (OpenInsider)** - insider_trades, insider_summary, top_insiders, insider_alerts
5. **Technical Indicators (Alpha Vantage)** - technical_indicators, company_fundamentals


## 🔌 API Endpoints

### Portfolio
- `GET /api/v1/portfolio/portfolios` - List all portfolios
- `GET /api/v1/portfolio/portfolios/{id}/holdings` - Get holdings
- `POST /api/v1/portfolio/sync` - Sync Wealthsimple data

### Market Data
- `GET /api/v1/market/stocks` - List all stocks (cached: 180s)
- `GET /api/v1/market/stocks/{ticker}` - Get stock info (cached: 300s)
- `GET /api/v1/market/stocks/{ticker}/price` - Price history (cached: 60s)
- `GET /api/v1/market/stocks/{ticker}/news` - Stock news (cached: 900s)

### Sentiment Analysis
- `GET /api/v1/sentiment/stock/{ticker}` - Get sentiment data
- `GET /api/v1/sentiment/trending` - Trending by sentiment
- `GET /api/v1/sentiment/metrics/collection` - Collection metrics

### Alpha Vantage
- `GET /api/v1/alphavantage/quote/{ticker}` - Real-time quote
- `GET /api/v1/alphavantage/fundamentals/{ticker}` - Company fundamentals
- `GET /api/v1/alphavantage/technical/{ticker}` - Technical indicators

### System
- `GET /api/v1/system/cache/stats` - Redis cache statistics
- `POST /api/v1/system/cache/clear` - Clear cache

Full API documentation available at http://localhost:8000/docs

## 📈 Performance Metrics

### API Response Times
|          Endpoint          | Uncached | Cached | Improvement |
|----------------------------|----------|--------|-------------|
| GET /stocks                |   250ms  |   25ms |     90%     |
| GET /stocks/{ticker}       |   80ms   |   12ms |     85%     |
| GET /stocks/{ticker}/price |   150ms  |   18ms |     88%     |

### Data Collection
- **Reddit Posts:** 1,944 posts/day 
- **Sentiment Accuracy:** 87.5% 
- **Cache Hit Rate:** 60-70%
- **Response Time Reduction:** 50-90% for cached requests

### Background Tasks
- Reddit collection: Every hour (2-3 min, 100 posts + comments)
- Portfolio sync: Every 5 minutes (30 sec)
- Market data update: Every hour (5 min)
- Alpha Vantage collection: Daily at 7am (10 min)

## Current Status

### In Progress

**Advanced Stock Screening**
- Screening endpoint design
- Multi-criteria filtering
- Frontend UI components

## Known Limitations

1. **Alpha Vantage Rate Limits** - Free tier: 25 requests/day
2. **Reddit API Limits** - 60 requests/minute
3. **Wealthsimple API** - Unofficial API (may break with updates)
4. **Single-User Only** - No authentication system (local deployment)
5. **Update Frequency** - Hourly updates (not suitable for day trading)

## 🔧 Project Structure

```
finance-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Core functionality (DB, cache, Celery)
│   │   ├── models.py         # Database models
│   │   ├── tasks.py          # Celery tasks
│   │   └── main.py           # FastAPI app
│   └── scripts/              # Setup scripts
├── frontend/                 # React application
├── collectors/               # Data collection modules
├── models/                   # SQLAlchemy models by domain
```


## 📄 License

Apache 2.0

---

**Version:** 1.0
**Last Updated:** 2026-01-01