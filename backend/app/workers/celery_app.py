from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "seo_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "crawl.*": {"queue": "crawl_scheduling"},
        "verify.*": {"queue": "backlink_verification"},
        "ml.*": {"queue": "ml_analysis"},
        "ai.*": {"queue": "ai_analysis"},
    },
    beat_schedule={
        # Re-verify 50 oldest-verified backlinks every 6 hours
        "verify-backlinks-every-6h": {
            "task": "verify.backlinks",
            "schedule": crontab(minute=0, hour="*/6"),
            "args": (None, 50),
            "options": {"queue": "backlink_verification"},
        },
        # Recompute PageRank graph every 24 hours at 02:00 UTC
        "recompute-pagerank-daily": {
            "task": "ml.recompute_pagerank",
            "schedule": crontab(minute=0, hour=2),
            "options": {"queue": "ml_analysis"},
        },
        # Snapshot domain_metrics for all tracked domains every 12 hours
        "snapshot-domain-metrics-every-12h": {
            "task": "ml.snapshot_domain_metrics",
            "schedule": crontab(minute=30, hour="*/12"),
            "options": {"queue": "ml_analysis"},
        },
        # Auto-recrawl overdue seed domains every 4 hours
        "auto-recrawl-seeds-every-4h": {
            "task": "crawl.auto_recrawl_seeds",
            "schedule": crontab(minute=0, hour="*/4"),
            "options": {"queue": "crawl_scheduling"},
        },
    },
)


@celery_app.task(name="crawl.ping")
def ping_worker():
    return {"status": "worker_ready"}