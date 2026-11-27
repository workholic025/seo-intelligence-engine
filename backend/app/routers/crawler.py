from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.security import validate_safe_external_url
from app.core.utils import clean_host
from app.database.session import get_db
from app.models.models import CrawlJob, SeedDomain
from app.schemas import CrawlStartRequest, CrawlStopRequest, SeedCreateRequest
from app.workers.tasks import task_run_crawl_job, task_verify_backlinks

router = APIRouter(prefix="/api/crawler", tags=["crawler"])


@router.post("/start")
def start_crawler(payload: CrawlStartRequest, db: Session = Depends(get_db)):
    safe_urls = []
    for raw in payload.seed_domains:
        try:
            safe_urls.append(validate_safe_external_url(raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    job = CrawlJob(
        target_domain=clean_host(safe_urls[0]),
        status="queued",
        max_pages=payload.max_pages,
        max_depth=payload.max_depth,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    task_run_crawl_job.delay(job.id, safe_urls, payload.max_pages, payload.max_depth)
    return {"job_id": job.id, "status": "queued", "seed_urls": safe_urls}


@router.post("/stop")
def stop_crawler(payload: CrawlStopRequest, db: Session = Depends(get_db)):
    job = db.query(CrawlJob).filter(CrawlJob.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Crawl job not found.")
    job.status = "stopped"
    db.commit()
    return {"job_id": job.id, "status": "stopped"}


@router.post("/verify")
def trigger_verification(domain: str | None = Query(None), batch_size: int = Query(50, ge=5, le=200)):
    task_verify_backlinks.delay(domain, batch_size)
    return {"status": "verification_queued", "target_domain": domain, "batch_size": batch_size}


@router.get("/status")
def crawler_status(db: Session = Depends(get_db)):
    running = db.query(CrawlJob).filter(CrawlJob.status.in_(["running", "queued"])).all()
    return {
        "active_jobs_count": len(running),
        "active_jobs": [
            {
                "id": j.id,
                "target_domain": j.target_domain,
                "status": j.status,
                "pages_crawled": j.pages_crawled,
                "links_discovered": j.links_discovered,
            }
            for j in running
        ],
    }


@router.get("/jobs")
def crawler_jobs(limit: int = Query(30, ge=5, le=100), db: Session = Depends(get_db)):
    jobs = db.query(CrawlJob).order_by(desc(CrawlJob.created_at)).limit(limit).all()
    return {
        "jobs": [
            {
                "id": j.id,
                "target_domain": j.target_domain,
                "status": j.status,
                "pages_crawled": j.pages_crawled,
                "links_discovered": j.links_discovered,
                "max_pages": j.max_pages,
                "max_depth": j.max_depth,
                "started_at": j.started_at,
                "finished_at": j.finished_at,
                "created_at": j.created_at,
            }
            for j in jobs
        ]
    }


@router.get("/seeds")
def list_seeds(db: Session = Depends(get_db)):
    seeds = db.query(SeedDomain).order_by(desc(SeedDomain.created_at)).all()
    return {"seeds": [{"id": s.id, "domain": s.domain, "seed_url": s.seed_url, "category": s.category} for s in seeds]}


@router.post("/seeds")
def add_seed(payload: SeedCreateRequest, db: Session = Depends(get_db)):
    try:
        safe_url = validate_safe_external_url(payload.domain)
        dom = clean_host(safe_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = db.query(SeedDomain).filter(SeedDomain.domain == dom).first()
    if existing:
        return {"id": existing.id, "domain": existing.domain, "message": "Already exists"}
    s = SeedDomain(domain=dom, seed_url=safe_url, category=payload.category)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "domain": s.domain, "seed_url": s.seed_url}


@router.delete("/seeds/{seed_id}", status_code=204)
def delete_seed(seed_id: int, db: Session = Depends(get_db)):
    seed = db.query(SeedDomain).filter(SeedDomain.id == seed_id).first()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed domain not found.")
    db.delete(seed)
    db.commit()
