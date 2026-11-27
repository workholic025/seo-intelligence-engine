from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.models import AuthorityScore, Backlink, CrawledPage, PageRankResult, TrackedDomain


def get_overview(domain: str, db: Session) -> dict:
    clean = domain.removeprefix("www.").lower().strip()
    tracked = db.query(TrackedDomain).filter(TrackedDomain.domain == clean).first()

    indexed_pages = db.query(func.count(CrawledPage.id)).filter(CrawledPage.domain == clean).scalar() or 0
    total_bl = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean).scalar() or 0
    unique_ref = db.query(func.count(func.distinct(Backlink.source_domain))).filter(Backlink.target_domain == clean).scalar() or 0
    unique_dest = db.query(func.count(func.distinct(Backlink.target_url))).filter(Backlink.target_domain == clean).scalar() or 0
    dofollow = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.is_dofollow.is_(True)).scalar() or 0
    nofollow = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.is_nofollow.is_(True)).scalar() or 0
    sponsored = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.is_sponsored.is_(True)).scalar() or 0
    ugc = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.is_ugc.is_(True)).scalar() or 0
    active = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.status == "active").scalar() or 0
    lost = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.status == "lost").scalar() or 0
    internal_sum = db.query(func.coalesce(func.sum(CrawledPage.internal_links_count), 0)).filter(CrawledPage.domain == clean).scalar() or 0
    external_sum = db.query(func.coalesce(func.sum(CrawledPage.external_links_count), 0)).filter(CrawledPage.domain == clean).scalar() or 0

    las = db.query(AuthorityScore).filter(AuthorityScore.domain == clean).order_by(desc(AuthorityScore.calculated_at)).first()
    pr = db.query(PageRankResult).filter(PageRankResult.domain == clean).order_by(desc(PageRankResult.calculated_at)).first()

    return {
        "domain": clean,
        "metric_source": "internal_local_index",
        "title": tracked.title if tracked else "",
        "meta_description": tracked.meta_description if tracked else "",
        "http_status": tracked.http_status if tracked else None,
        "https_available": tracked.https_available if tracked else None,
        "registration_age_days": tracked.registration_age_days if tracked else None,
        "indexed_pages": indexed_pages,
        "total_discovered_backlinks": total_bl,
        "unique_referring_domains": unique_ref,
        "unique_destination_urls": unique_dest,
        "dofollow_backlinks": dofollow,
        "nofollow_backlinks": nofollow,
        "sponsored_backlinks": sponsored,
        "ugc_backlinks": ugc,
        "active_backlinks": active,
        "lost_backlinks": lost,
        "internal_links": int(internal_sum),
        "external_links": int(external_sum),
        "local_authority_score": {
            "score": las.las_score if las else None,
            "confidence": las.confidence_level if las else "insufficient_data",
            "formula_version": las.formula_version if las else "LAS-v1.0-experimental",
            "label": "Internally calculated experimental metric (Not Moz DA / Ahrefs DR / Semrush AS)",
        },
        "internal_pagerank": {
            "score": pr.pagerank_score if pr else None,
            "label": "Internal graph PageRank (Not Google PageRank)",
        },
    }
