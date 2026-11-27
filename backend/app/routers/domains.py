from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.algorithms.engine import (
    analyze_anchor_texts,
    calculate_local_authority_score,
    compute_backlink_quality_scores,
    compute_networkx_pagerank,
)
from app.core.utils import clean_host
from app.database.session import get_db
from app.ml.engine import cluster_indexed_domains, compute_content_relevance, run_spam_and_anomaly_analysis
from app.models.models import AuthorityScore, Backlink, BacklinkHistory, DomainMetric, PageRankResult, ReferringDomain, TrackedDomain
from app.schemas import AnalyzeRequest
from app.services.domain_service import get_overview

router = APIRouter(prefix="/api", tags=["domains"])


@router.post("/domains/analyze")
def analyze_domain(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        domain = clean_host(payload.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not db.query(TrackedDomain).filter(TrackedDomain.domain == domain).first():
        db.add(TrackedDomain(domain=domain))
        db.commit()
    return get_overview(domain, db)


@router.get("/domains/{domain}/overview")
def domain_overview(domain: str, db: Session = Depends(get_db)):
    return get_overview(domain, db)


@router.get("/domains/{domain}/backlinks")
def get_domain_backlinks(
    domain: str,
    status_filter: str | None = Query(None),
    link_attr: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("last_verified_at"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db),
):
    clean = domain.removeprefix("www.").lower().strip()
    q = db.query(Backlink).filter(Backlink.target_domain == clean)

    if status_filter and status_filter != "all":
        q = q.filter(Backlink.status == status_filter)
    if link_attr == "dofollow":
        q = q.filter(Backlink.is_dofollow.is_(True))
    elif link_attr == "nofollow":
        q = q.filter(Backlink.is_nofollow.is_(True))
    elif link_attr == "sponsored":
        q = q.filter(Backlink.is_sponsored.is_(True))
    elif link_attr == "ugc":
        q = q.filter(Backlink.is_ugc.is_(True))
    if search:
        q = q.filter(
            (Backlink.source_domain.ilike(f"%{search}%"))
            | (Backlink.anchor_text.ilike(f"%{search}%"))
            | (Backlink.target_url.ilike(f"%{search}%"))
        )

    sort_col = getattr(Backlink, sort_by, Backlink.last_verified_at)
    total = q.count()
    rows = q.order_by(desc(sort_col)).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": b.id,
                "source_domain": b.source_domain,
                "source_url": b.source_url,
                "target_domain": b.target_domain,
                "target_url": b.target_url,
                "anchor_text": b.anchor_text,
                "link_type": b.link_type,
                "is_dofollow": b.is_dofollow,
                "is_nofollow": b.is_nofollow,
                "is_sponsored": b.is_sponsored,
                "is_ugc": b.is_ugc,
                "source_http_status": b.source_http_status,
                "status": b.status,
                "placement_context": b.placement_context,
                "first_discovered_at": b.first_discovered_at,
                "last_verified_at": b.last_verified_at,
            }
            for b in rows
        ],
    }


@router.get("/backlinks/{backlink_id}")
def get_backlink_detail(backlink_id: int, db: Session = Depends(get_db)):
    bl = db.query(Backlink).filter(Backlink.id == backlink_id).first()
    if not bl:
        raise HTTPException(status_code=404, detail="Backlink not found.")
    history = (
        db.query(BacklinkHistory)
        .filter(BacklinkHistory.backlink_id == backlink_id)
        .order_by(desc(BacklinkHistory.recorded_at))
        .all()
    )
    return {
        "backlink": {
            "id": bl.id,
            "source_domain": bl.source_domain,
            "source_url": bl.source_url,
            "target_domain": bl.target_domain,
            "target_url": bl.target_url,
            "anchor_text": bl.anchor_text,
            "anchor_attributes": bl.anchor_attributes,
            "link_type": bl.link_type,
            "is_dofollow": bl.is_dofollow,
            "is_nofollow": bl.is_nofollow,
            "is_sponsored": bl.is_sponsored,
            "is_ugc": bl.is_ugc,
            "status": bl.status,
            "placement_context": bl.placement_context,
            "first_discovered_at": bl.first_discovered_at,
            "last_verified_at": bl.last_verified_at,
        },
        "history": [
            {
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "previous_anchor": h.previous_anchor,
                "new_anchor": h.new_anchor,
                "http_status": h.http_status,
                "recorded_at": h.recorded_at,
            }
            for h in history
        ],
    }


@router.get("/domains/{domain}/referring-domains")
def get_referring_domains(
    domain: str,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db),
):
    clean = domain.removeprefix("www.").lower().strip()
    q = db.query(ReferringDomain).filter(ReferringDomain.target_domain == clean)
    if search:
        q = q.filter(ReferringDomain.source_domain.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(desc(ReferringDomain.total_backlinks)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "domain": clean,
        "total_unique_referring_domains": total,
        "items": [
            {
                "source_domain": r.source_domain,
                "total_backlinks": r.total_backlinks,
                "dofollow_backlinks": r.dofollow_backlinks,
                "nofollow_backlinks": r.nofollow_backlinks,
                "status": r.status,
                "first_seen_at": r.first_seen_at,
                "last_seen_at": r.last_seen_at,
            }
            for r in items
        ],
    }


@router.get("/domains/{domain}/authority")
def get_domain_authority(domain: str, recalculate: bool = Query(True), db: Session = Depends(get_db)):
    if recalculate:
        return calculate_local_authority_score(db, domain)
    clean = domain.removeprefix("www.").lower().strip()
    las = db.query(AuthorityScore).filter(AuthorityScore.domain == clean).order_by(desc(AuthorityScore.calculated_at)).first()
    if not las:
        return calculate_local_authority_score(db, clean)
    return {
        "domain": clean,
        "las_score": las.las_score,
        "components": {"R": las.r_component, "Q": las.q_component, "D": las.d_component, "S": las.s_component, "G": las.g_component},
        "formula_version": las.formula_version,
        "confidence_level": las.confidence_level,
        "data_coverage": las.data_coverage,
        "calculated_at": las.calculated_at,
    }


@router.get("/domains/{domain}/pagerank")
def get_domain_pagerank(domain: str, recalculate: bool = Query(False), db: Session = Depends(get_db)):
    meta = compute_networkx_pagerank(db) if recalculate else None
    clean = domain.removeprefix("www.").lower().strip()
    pr = db.query(PageRankResult).filter(PageRankResult.domain == clean).order_by(desc(PageRankResult.calculated_at)).first()
    top_domains = db.query(PageRankResult).order_by(desc(PageRankResult.pagerank_score)).limit(20).all()
    return {
        "domain": clean,
        "pagerank_score": pr.pagerank_score if pr else None,
        "damping_factor": pr.damping_factor if pr else 0.85,
        "graph_meta": meta,
        "top_indexed_domains": [{"domain": t.domain, "pagerank_score": t.pagerank_score} for t in top_domains],
        "disclaimer": "Internal PageRank over local crawl graph only (Not Google PageRank).",
    }


@router.get("/domains/{domain}/quality")
def get_domain_quality(domain: str, db: Session = Depends(get_db)):
    return {
        "quality": compute_backlink_quality_scores(db, domain),
        "anchors": analyze_anchor_texts(db, domain),
    }


@router.get("/domains/{domain}/spam-analysis")
def get_domain_spam_analysis(domain: str, db: Session = Depends(get_db)):
    return {
        "spam_and_anomalies": run_spam_and_anomaly_analysis(db, domain),
        "domain_clusters": cluster_indexed_domains(db),
    }


@router.get("/domains/{domain}/content-relevance")
def get_content_relevance(
    domain: str,
    source_url: str = Query(..., description="Full URL of the source page to compare"),
    db: Session = Depends(get_db),
):
    return compute_content_relevance(db, source_url=source_url, target_domain=domain)


@router.get("/domains/{domain}/metrics-history")
def get_domain_metrics_history(
    domain: str,
    limit: int = Query(30, ge=5, le=90),
    db: Session = Depends(get_db),
):
    clean = domain.removeprefix("www.").lower().strip()
    rows = (
        db.query(DomainMetric)
        .filter(DomainMetric.domain == clean)
        .order_by(desc(DomainMetric.recorded_at))
        .limit(limit)
        .all()
    )
    return {
        "domain": clean,
        "history": [
            {
                "recorded_at": r.recorded_at,
                "total_backlinks": r.total_backlinks,
                "unique_referring_domains": r.unique_referring_domains,
                "active_count": r.active_count,
                "lost_count": r.lost_count,
                "dofollow_count": r.dofollow_count,
                "nofollow_count": r.nofollow_count,
            }
            for r in reversed(rows)
        ],
    }


@router.get("/domains/{domain}/authority-history")
def get_authority_history(
    domain: str,
    limit: int = Query(30, ge=5, le=90),
    db: Session = Depends(get_db),
):
    clean = domain.removeprefix("www.").lower().strip()
    rows = (
        db.query(AuthorityScore)
        .filter(AuthorityScore.domain == clean)
        .order_by(desc(AuthorityScore.calculated_at))
        .limit(limit)
        .all()
    )
    return {
        "domain": clean,
        "history": [
            {
                "recorded_at": r.calculated_at,
                "las_score": r.las_score,
                "confidence_level": r.confidence_level,
                "data_coverage": r.data_coverage,
            }
            for r in reversed(rows)
        ],
    }
