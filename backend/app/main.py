import threading
import time
from collections import OrderedDict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.database.session import Base, SessionLocal, engine
from app.routers import ai, auth, competitors, crawler, dashboard, domains, export, ml, projects

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Self-Hosted SEO Authority, Backlink Crawler, ML & DeepSeek AI Intelligence Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory rate limiter — 120 req/60s per IP, OrderedDict with 10k-IP LRU cap
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_rate_buckets: OrderedDict[str, list[float]] = OrderedDict()
_RATE_LIMIT = 120
_RATE_WINDOW = 60.0
_MAX_IPS = 10_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with _rate_lock:
            if client_ip in _rate_buckets:
                _rate_buckets.move_to_end(client_ip)
            else:
                if len(_rate_buckets) >= _MAX_IPS:
                    _rate_buckets.popitem(last=False)
                _rate_buckets[client_ip] = []

            timestamps = _rate_buckets[client_ip]
            cutoff = now - _RATE_WINDOW
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if len(timestamps) >= _RATE_LIMIT:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                    headers={"Retry-After": str(int(_RATE_WINDOW))},
                )
            timestamps.append(now)
        return await call_next(request)


app.add_middleware(RateLimitMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(domains.router)
app.include_router(crawler.router)
app.include_router(ml.router)
app.include_router(ai.router)
app.include_router(competitors.router)
app.include_router(projects.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_ok = True
    except OperationalError:
        pass
    return {"status": "ok" if db_ok else "degraded", "db": "connected" if db_ok else "unreachable", "environment": settings.ENVIRONMENT}
