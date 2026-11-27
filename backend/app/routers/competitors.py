from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Backlink
from app.services.domain_service import get_overview

router = APIRouter(prefix="/api/competitors", tags=["competitors"])


@router.get("/compare")
def compare_competitors(
    domains: str = Query(..., description="Comma-separated list of up to 5 domains"),
    db: Session = Depends(get_db),
):
    raw_list = [d.removeprefix("www.").lower().strip() for d in domains.split(",") if d.strip()]
    unique_domains = list(dict.fromkeys(raw_list))[:5]
    if len(unique_domains) < 2:
        raise HTTPException(status_code=400, detail="Provide between 2 and 5 domains separated by commas.")

    profiles = []
    ref_sets: dict[str, set[str]] = {}
    anchor_sets: dict[str, set[str]] = {}

    for dom in unique_domains:
        ov = get_overview(dom, db)
        refs = {r[0] for r in db.query(Backlink.source_domain).filter(Backlink.target_domain == dom).distinct().all()}
        anchors = {
            a[0].lower()
            for a in db.query(Backlink.anchor_text)
            .filter(Backlink.target_domain == dom, Backlink.anchor_text != "")
            .distinct()
            .all()
        }
        ref_sets[dom] = refs
        anchor_sets[dom] = anchors
        profiles.append(ov)

    common_refs = sorted(set.intersection(*ref_sets.values())) if ref_sets else []
    common_anchors = sorted(set.intersection(*anchor_sets.values()))[:30] if anchor_sets else []
    page_counts = [p["indexed_pages"] for p in profiles]
    coverage_warning = (
        "Index coverage differs significantly across compared domains; interpret metrics relative to local crawl depth."
        if (max(page_counts) - min(page_counts)) > 10 or min(page_counts) == 0
        else None
    )

    return {
        "domains": unique_domains,
        "coverage_warning": coverage_warning,
        "profiles": profiles,
        "common_referring_domains": common_refs[:100],
        "common_anchor_texts": common_anchors,
    }
