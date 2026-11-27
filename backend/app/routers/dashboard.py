from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import AiAnalysis, AuthorityScore, Backlink, CrawlJob, CrawledPage, MlTrainingLabel, ReferringDomain

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total_pages = db.query(func.count(CrawledPage.id)).scalar() or 0
    total_bl = db.query(func.count(Backlink.id)).scalar() or 0
    ref_doms = db.query(func.count(func.distinct(Backlink.source_domain))).scalar() or 0
    active_bl = db.query(func.count(Backlink.id)).filter(Backlink.status == "active").scalar() or 0
    lost_bl = db.query(func.count(Backlink.id)).filter(Backlink.status == "lost").scalar() or 0
    dofollow_bl = db.query(func.count(Backlink.id)).filter(Backlink.is_dofollow.is_(True)).scalar() or 0
    nofollow_bl = db.query(func.count(Backlink.id)).filter(Backlink.is_nofollow.is_(True)).scalar() or 0
    avg_las = db.query(func.avg(AuthorityScore.las_score)).filter(AuthorityScore.las_score.isnot(None)).scalar()
    running_jobs = db.query(func.count(CrawlJob.id)).filter(CrawlJob.status == "running").scalar() or 0
    total_jobs = db.query(func.count(CrawlJob.id)).scalar() or 0

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_bl = db.query(func.count(Backlink.id)).filter(Backlink.first_discovered_at >= seven_days_ago).scalar() or 0

    db_usage = {
        "backlinks": total_bl,
        "crawled_pages": db.query(func.count(CrawledPage.id)).scalar() or 0,
        "referring_domains": db.query(func.count(ReferringDomain.id)).scalar() or 0,
        "ai_analyses": db.query(func.count(AiAnalysis.id)).scalar() or 0,
        "ml_predictions": db.query(func.count(func.distinct(MlTrainingLabel.backlink_id))).scalar() or 0,
    }

    return {
        "total_indexed_pages": total_pages,
        "total_backlinks": total_bl,
        "referring_domains": ref_doms,
        "active_backlinks": active_bl,
        "lost_backlinks": lost_bl,
        "dofollow_backlinks": dofollow_bl,
        "nofollow_backlinks": nofollow_bl,
        "average_las": round(float(avg_las), 2) if avg_las is not None else None,
        "running_crawl_jobs": running_jobs,
        "total_crawl_jobs": total_jobs,
        "newly_discovered_backlinks": new_bl,
        "database_usage": db_usage,
    }
