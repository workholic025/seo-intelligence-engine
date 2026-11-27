# SEO Intelligence Engine

Self-hosted SEO authority checker, backlink search engine, and crawler with machine learning and DeepSeek AI integration.

## What it does

- **Domain Authority Checker** — Local Authority Score (LAS) using logarithmic multi-factor scoring
- **Backlink Search Engine** — Filter, sort, verify, and export backlinks with full history tracking
- **Own Web Crawler** — Scrapy-powered BFS crawler with sitemap parsing, URL normalization, and robots.txt compliance
- **Backlink Verification** — Periodic live re-checks with status history (active / lost / redirected)
- **Referring Domain Analyzer** — Unique domain distribution, DoFollow/NoFollow breakdown
- **Competitor Comparison** — Side-by-side analysis for up to 5 domains
- **Internal PageRank** — NetworkX directed graph (damping factor 0.85, internal index only)
- **ML Spam Detection** — Isolation Forest anomaly detection + Random Forest classifier on human labels
- **DeepSeek AI Reports** — Structured JSON assessments of backlink profiles and SEO recommendations

> All scores (LAS, LQS, PageRank) are **internally calculated experimental metrics** based solely on the local crawl index. They are not Moz DA, Ahrefs DR, Semrush Authority Score, or Google PageRank.

---

## Requirements

| Software | Version | Notes |
|----------|---------|-------|
| Docker Desktop | Latest | WSL2 backend enabled |
| Docker Compose | V2 plugin | Included with Docker Desktop |
| Python | 3.11+ | For local dev only |
| Node.js | 18 LTS+ | For local dev only |

Hardware: Intel Core i5 (any gen), 16 GB RAM, any GPU (CPU-only ML).

---

## Quick Start (Docker — Recommended)

```powershell
# 1. Clone / navigate to project root
cd seo-intelligence-engine

# 2. Run setup (checks prerequisites, creates .env, builds, starts)
.\scripts\setup.ps1
```

After setup completes:

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

Default credentials: `admin@seo.local` / `Admin@SEO123`
**Change this password after first login.**

---

## Manual Setup (Step by Step)

### 1. Create environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure:

```env
DEEPSEEK_API_KEY=your_key_here          # Required for AI features
SECRET_KEY=replace_with_64_char_random  # Change before production
```

### 2. Start all services

```powershell
docker compose up -d --build
```

### 3. Create the admin user

```powershell
docker compose exec backend python scripts/init_db.py
```

### 4. Verify services are running

```powershell
docker compose ps
```

All six services should show `running`: `postgres`, `redis`, `backend`, `celery_worker`, `celery_beat`, `frontend`.

---

## Common Commands

```powershell
# Start
docker compose up -d

# Stop (keeps database volumes)
docker compose down

# Stop and DELETE all data
docker compose down -v

# Rebuild after code changes
docker compose up -d --build

# View backend logs
docker compose logs -f backend

# View crawler worker logs
docker compose logs -f celery_worker

# Run database migrations
docker compose exec backend alembic upgrade head

# Open backend shell
docker compose exec backend python
```

---

## Local Development (Without Docker)

Requires PostgreSQL 16 and Redis 7 running locally.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
# Set DATABASE_URL and REDIS_URL in .env to point to local services
uvicorn app.main:app --reload --port 8000

# In a separate terminal — Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q crawl_scheduling,backlink_verification,ml_analysis,ai_analysis

# Frontend
cd frontend
npm install
npm run dev
```

---

## Running Database Migrations

The app auto-creates tables on first start via SQLAlchemy. To use Alembic for schema management:

```powershell
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Check current migration version
docker compose exec backend alembic current

# Generate a new migration after model changes
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

---

## Running Tests

```powershell
docker compose exec backend pytest tests/ -v
```

---

## First Use Workflow

1. Open http://localhost:5173 and sign in
2. Go to **Crawler & Seeds** → add seed domains (websites you have permission to crawl)
3. Launch a crawl job (start with `max_pages=200`, `max_depth=2` to test)
4. Once pages are indexed, go to **Domain Authority** and analyze any crawled domain
5. Use **Backlink Explorer** to filter, inspect, and export discovered backlinks
6. Go to **ML Spam & Anomalies** to run the spam analysis
7. Use **DeepSeek AI Reports** for structured AI assessments (requires DEEPSEEK_API_KEY)

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | _(empty)_ | DeepSeek API key — AI features disabled without it |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model identifier from DeepSeek API docs |
| `SECRET_KEY` | _(example value)_ | JWT signing key — **change before use** |
| `CRAWLER_CONCURRENCY` | `4` | Max parallel Scrapy requests |
| `CRAWLER_DOWNLOAD_DELAY` | `1.5` | Seconds between requests per domain |
| `CRAWLER_MAX_PAGES_PER_JOB` | `10000` | Hard cap on pages per crawl job |
| `CELERY_WORKER_CONCURRENCY` | `2` | Celery worker threads (conservative for 16 GB RAM) |

---

## Architecture

```
seo-intelligence-engine/
├── backend/              Python FastAPI + Celery
│   └── app/
│       ├── ai/           DeepSeek API integration
│       ├── algorithms/   LAS, LQS, PageRank
│       ├── core/         Config, auth, SSRF validation
│       ├── crawler/      Scrapy spider + runner
│       ├── ml/           Spam detection, clustering, TF-IDF
│       ├── models/       SQLAlchemy ORM (19 tables)
│       ├── services/     Backlink verification
│       └── workers/      Celery tasks + queue routing
├── frontend/             React + TypeScript + Vite + Tailwind
├── migrations/           Alembic schema migrations
├── scripts/              Setup and init helpers
├── tests/                Pytest test suite
├── docker/               Dockerfile.backend, Dockerfile.frontend
└── docker-compose.yml    Full service orchestration
```

---

## Security Notes

- Crawler enforces SSRF protection: blocks localhost, private IP ranges, and cloud metadata endpoints
- All credentials must be in `.env` — never commit `.env` to version control
- PostgreSQL and Redis are on an internal Docker network, not exposed to the internet
- Change `SECRET_KEY` and `POSTGRES_PASSWORD` before exposing the app to any network
