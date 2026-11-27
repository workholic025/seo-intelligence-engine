import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.ai.deepseek_service import run_deepseek_analysis
from app.algorithms.engine import calculate_local_authority_score, compute_networkx_pagerank
from app.crawler.runner import run_spider_subprocess
from app.database.session import SessionLocal
from app.ml.engine import run_spam_and_anomaly_analysis
from app.models.models import Backlink, CrawlJob, DomainMetric, SeedDomain, TrackedDomain
from app.services.verifier import verify_backlinks_batch
from app.workers.celery_app import celery_app


@celery_app.task(name="crawl.run_job", bind=True, max_retries=2, default_retry_delay=30)
def task_run_crawl_job(self, job_id: int, seed_urls: list[str], max_pages: int = 500, max_depth: int = 3):
    code = run_spider_subprocess(job_id=job_id, seed_urls=seed_urls, max_pages=max_pages, max_depth=max_depth)
    if code != 0:
        db = SessionLocal()
        try:
            job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
            if job and job.status == "running":
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
    return {"job_id": job_id, "exit_code": code}


@celery_app.task(name="verify.backlinks", bind=True, max_retries=2, default_retry_delay=60)
def task_verify_backlinks(self, target_domain: str | None = None, batch_size: int = 50):
    db = SessionLocal()
    try:
        return verify_backlinks_batch(db, target_domain=target_domain, batch_size=batch_size)
    finally:
        db.close()


@celery_app.task(name="ml.recompute_authority", bind=True, max_retries=1)
def task_recompute_authority(self, domain: str):
    db = SessionLocal()
    try:
        pr = compute_networkx_pagerank(db)
        las = calculate_local_authority_score(db, domain)
        ml = run_spam_and_anomaly_analysis(db, domain)
        return {"pagerank": pr, "las": las, "ml": ml}
    finally:
        db.close()


@celery_app.task(name="ai.run_analysis", bind=True, max_retries=2, default_retry_delay=15)
def task_run_ai_analysis(self, domain: str, analysis_type: str, context_payload: dict):
    db = SessionLocal()
    try:
        return asyncio.run(run_deepseek_analysis(db, domain, analysis_type, context_payload))
    finally:
        db.close()


@celery_app.task(name="ml.recompute_pagerank", bind=True, max_retries=1)
def task_recompute_pagerank(self):
    """Scheduled: recompute PageRank graph over all indexed pages."""
    db = SessionLocal()
    try:
        return compute_networkx_pagerank(db)
    finally:
        db.close()


@celery_app.task(name="ml.snapshot_domain_metrics", bind=True, max_retries=1)
def task_snapshot_domain_metrics(self):
    """Scheduled: write a DomainMetric snapshot for every tracked domain."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        domains = db.query(TrackedDomain.domain).all()
        snapped = 0
        for (domain,) in domains:
            total_bl = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain).scalar() or 0
            unique_ref = db.query(func.count(func.distinct(Backlink.source_domain))).filter(Backlink.target_domain == domain).scalar() or 0
            dofollow = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain, Backlink.is_dofollow.is_(True)).scalar() or 0
            nofollow = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain, Backlink.is_nofollow.is_(True)).scalar() or 0
            sponsored = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain, Backlink.is_sponsored.is_(True)).scalar() or 0
            ugc = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain, Backlink.is_ugc.is_(True)).scalar() or 0
            active = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain, Backlink.status == "active").scalar() or 0
            lost = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == domain, Backlink.status == "lost").scalar() or 0

            db.add(DomainMetric(
                domain=domain,
                total_backlinks=total_bl,
                unique_referring_domains=unique_ref,
                dofollow_count=dofollow,
                nofollow_count=nofollow,
                sponsored_count=sponsored,
                ugc_count=ugc,
                active_count=active,
                lost_count=lost,
                recorded_at=now,
            ))
            snapped += 1
        db.commit()
        return {"snapped_domains": snapped}
    finally:
        db.close()


@celery_app.task(name="crawl.auto_recrawl_seeds", bind=True, max_retries=1)
def task_auto_recrawl_seeds(self, max_pages: int = 200, max_depth: int = 2):
    """Scheduled: queue a new crawl job for every active seed that is overdue for a recrawl."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        seeds = db.query(SeedDomain).filter(SeedDomain.is_active.is_(True)).all()
        queued = 0
        for seed in seeds:
            if seed.last_crawled_at is None:
                overdue = True
            else:
                interval = timedelta(hours=seed.recrawl_interval_hours or 168)
                overdue = (now - seed.last_crawled_at) >= interval

            if not overdue:
                continue

            job = CrawlJob(
                target_domain=seed.domain,
                status="queued",
                pages_crawled=0,
                links_discovered=0,
                started_at=now,
            )
            db.add(job)
            seed.last_crawled_at = now
            db.commit()
            db.refresh(job)

            task_run_crawl_job.apply_async(
                args=[job.id, [seed.seed_url], max_pages, max_depth],
                queue="crawl_scheduling",
            )
            queued += 1

        return {"queued_jobs": queued}
    finally:
        db.close()