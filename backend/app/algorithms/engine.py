import math
from collections import Counter
from datetime import datetime, timedelta, timezone

import networkx as nx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import AuthorityScore, Backlink, CrawledPage, PageRankResult

DEFAULT_LAS_WEIGHTS = {"R": 0.30, "Q": 0.25, "D": 0.20, "S": 0.15, "G": 0.10}
DEFAULT_LQS_WEIGHTS = {"R": 0.30, "C": 0.25, "T": 0.20, "P": 0.15, "H": 0.10}
GENERIC_ANCHORS = {
    "click here", "here", "read more", "learn more", "website", "visit",
    "more", "link", "source", "this page", "view", "details", "homepage",
}


def compute_networkx_pagerank(
    db: Session,
    damping_factor: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> dict:
    """Computes internal PageRank using NetworkX over indexed pages and backlink edges."""
    G = nx.DiGraph()

    pages = db.query(CrawledPage.url, CrawledPage.domain).all()
    for url, _ in pages:
        G.add_node(url)

    # Deduplicate edges automatically via DiGraph
    links = db.query(Backlink.source_url, Backlink.target_url).filter(Backlink.status == "active").all()
    for src, tgt in links:
        if src != tgt:
            G.add_edge(src, tgt)

    if G.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "domains_updated": 0}

    # NetworkX automatically handles dangling nodes with uniform redistribution
    pr_scores = nx.pagerank(G, alpha=damping_factor, max_iter=max_iter, tol=tol)

    # Aggregate page-level PageRank to domain level
    domain_agg: dict[str, float] = {}
    now = datetime.now(timezone.utc)

    for url, score in pr_scores.items():
        # Extract host cleanly
        dom = url.split("//")[-1].split("/")[0].removeprefix("www.").lower()
        domain_agg[dom] = domain_agg.get(dom, 0.0) + float(score)

    db.query(PageRankResult).delete()
    for dom, agg_score in domain_agg.items():
        db.add(
            PageRankResult(
                domain=dom,
                page_url=None,
                pagerank_score=round(agg_score, 8),
                damping_factor=damping_factor,
                iterations=max_iter,
                calculated_at=now,
            )
        )
    db.commit()

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "domains_updated": len(domain_agg),
        "damping_factor": damping_factor,
        "disclaimer": "Internal graph PageRank computed strictly from our local index (Not Google PageRank).",
    }


def analyze_anchor_texts(db: Session, domain: str) -> dict:
    clean = domain.removeprefix("www.").lower().strip()
    brand_token = clean.split(".")[0]
    rows = db.query(Backlink.anchor_text, Backlink.link_type).filter(Backlink.target_domain == clean).all()

    counts = {
        "exact_match": 0,
        "partial_match": 0,
        "branded": 0,
        "generic": 0,
        "naked_url": 0,
        "image_link": 0,
        "empty": 0,
    }
    raw_counter: Counter[str] = Counter()

    for anchor_raw, ltype in rows:
        a = (anchor_raw or "").strip().lower()
        if a:
            raw_counter[a] += 1

        if ltype == "image" and not a:
            counts["image_link"] += 1
        elif not a:
            counts["empty"] += 1
        elif a.startswith(("http://", "https://", "www.")) or a == clean:
            counts["naked_url"] += 1
        elif a in GENERIC_ANCHORS:
            counts["generic"] += 1
        elif a == brand_token:
            counts["exact_match"] += 1
        elif brand_token in a:
            counts["branded"] += 1
        else:
            counts["partial_match"] += 1

    total = len(rows)
    unusual_patterns = []
    if total >= 10:
        top_anchor, top_cnt = raw_counter.most_common(1)[0] if raw_counter else ("", 0)
        if top_cnt / total > 0.50:
            unusual_patterns.append(
                f"High anchor repetition: '{top_anchor}' accounts for {round(top_cnt / total * 100, 1)}% of anchors (observation only, not confirmed spam)."
            )
        if counts["exact_match"] / total > 0.35:
            unusual_patterns.append("Elevated exact-match anchor ratio observed relative to branded/generic mix.")

    return {
        "domain": clean,
        "total_anchors": total,
        "distribution": counts,
        "top_anchors": [{"anchor": k, "count": v} for k, v in raw_counter.most_common(15)],
        "unusual_patterns": unusual_patterns,
    }


def compute_backlink_quality_scores(
    db: Session,
    domain: str,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    LQS = 0.30R + 0.25C + 0.20T + 0.15P + 0.10H
    Treats missing evidence as unknown (re-normalizes weights across available signals).
    Does not treat NoFollow as automatically worthless.
    """
    w = weights or DEFAULT_LQS_WEIGHTS
    clean = domain.removeprefix("www.").lower().strip()
    brand = clean.split(".")[0]

    backlinks = db.query(Backlink).filter(Backlink.target_domain == clean).limit(250).all()
    if not backlinks:
        return {"domain": clean, "average_lqs": None, "status": "insufficient_data", "items": []}

    # Pre-fetch source domain PageRank as reputation proxy R
    pr_map = {
        r.domain: r.pagerank_score
        for r in db.query(PageRankResult).filter(PageRankResult.page_url.is_(None)).all()
    }
    max_pr = max(pr_map.values()) if pr_map else 0.0

    scored = []
    for bl in backlinks:
        known: dict[str, float] = {}

        # R: source domain reputation from our index
        if bl.source_domain in pr_map and max_pr > 0:
            known["R"] = min(1.0, math.log1p(pr_map[bl.source_domain] * 1e4) / math.log1p(max_pr * 1e4 + 1e-9))

        # C: topical relevance (if placement context exists, check overlap with brand/domain keywords)
        if bl.placement_context:
            ctx = bl.placement_context.lower()
            known["C"] = 0.80 if brand in ctx else 0.50

        # T: anchor text relevance
        anchor = (bl.anchor_text or "").strip().lower()
        if anchor:
            if brand in anchor:
                known["T"] = 0.85
            elif anchor in GENERIC_ANCHORS:
                known["T"] = 0.45
            else:
                known["T"] = 0.65

        # P: contextual placement quality (body context + modest adjustment, NoFollow still retains value)
        if bl.placement_context and len(bl.placement_context) > 40:
            known["P"] = 0.85 if bl.is_dofollow else 0.65
        else:
            known["P"] = 0.60 if bl.is_dofollow else 0.45

        # H: historical stability
        if bl.first_discovered_at and bl.last_verified_at:
            age_days = max(0, (bl.last_verified_at - bl.first_discovered_at).days)
            known["H"] = min(1.0, 0.40 + 0.60 * (math.log1p(age_days) / math.log1p(90))) if bl.status == "active" else 0.20

        # Weighted average across ONLY known components
        total_w = sum(w[k] for k in known)
        lqs_val = round(sum(w[k] * known[k] for k in known) / total_w, 4) if total_w > 0 else None
        unknown_signals = [k for k in w if k not in known]

        scored.append({
            "backlink_id": bl.id,
            "source_domain": bl.source_domain,
            "source_url": bl.source_url,
            "anchor_text": bl.anchor_text,
            "is_dofollow": bl.is_dofollow,
            "lqs_score": round(lqs_val * 100, 1) if lqs_val is not None else None,
            "components": known,
            "unknown_signals": unknown_signals,
        })

    valid = [s["lqs_score"] for s in scored if s["lqs_score"] is not None]
    avg_lqs = round(sum(valid) / len(valid), 2) if valid else None
    return {
        "domain": clean,
        "average_lqs": avg_lqs,
        "formula": "LQS = 0.30R + 0.25C + 0.20T + 0.15P + 0.10H (experimental)",
        "items": scored,
    }


def calculate_local_authority_score(
    db: Session,
    domain: str,
    weights: dict[str, float] | None = None,
    min_backlinks_required: int = 3,
) -> dict:
    """
    LAS = 100 * (0.30*R + 0.25*Q + 0.20*D + 0.15*S + 0.10*G)
    Returns None and 'insufficient_data' if minimum index requirements are not met.
    """
    w = weights or DEFAULT_LAS_WEIGHTS
    clean = domain.removeprefix("www.").lower().strip()
    now = datetime.now(timezone.utc)

    total_bl = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean).scalar() or 0
    unique_ref = db.query(func.count(func.distinct(Backlink.source_domain))).filter(Backlink.target_domain == clean).scalar() or 0
    active_bl = db.query(func.count(Backlink.id)).filter(Backlink.target_domain == clean, Backlink.status == "active").scalar() or 0

    total_indexed_domains = max(1, db.query(func.count(func.distinct(Backlink.source_domain))).scalar() or 1)
    data_coverage = round(min(1.0, unique_ref / max(10, total_indexed_domains)), 4)

    if total_bl < min_backlinks_required or unique_ref < 1:
        record = AuthorityScore(
            domain=clean,
            las_score=None,
            formula_version="LAS-v1.0-experimental",
            confidence_level="insufficient_data",
            data_coverage=data_coverage,
            calculated_at=now,
        )
        db.add(record)
        db.commit()
        return {
            "domain": clean,
            "las_score": None,
            "status": "insufficient_data",
            "reason": f"Minimum {min_backlinks_required} indexed backlinks required; found {total_bl}.",
            "formula_version": "LAS-v1.0-experimental",
            "confidence_level": "insufficient_data",
            "data_coverage": data_coverage,
            "calculated_at": now.isoformat(),
            "label": "Internally calculated experimental metric (Not Moz DA / Ahrefs DR / Semrush AS)",
        }

    # R: Logarithmic normalized referring domain score (avoids raw volume gaming)
    max_ref_in_db = (
        db.query(func.count(func.distinct(Backlink.source_domain)))
        .group_by(Backlink.target_domain)
        .order_by(func.count(func.distinct(Backlink.source_domain)).desc())
        .first()
    )
    denom_ref = max(10, int(max_ref_in_db[0]) if max_ref_in_db else 10)
    R = min(1.0, math.log1p(unique_ref) / math.log1p(denom_ref))

    # Q: Average Backlink Quality Score (0..1)
    lqs_data = compute_backlink_quality_scores(db, clean)
    Q = (lqs_data["average_lqs"] / 100.0) if lqs_data["average_lqs"] is not None else 0.5

    # D: Referring domain diversity (unique referring domains / total backlinks, log-damped)
    D = min(1.0, (unique_ref / max(1, total_bl)) ** 0.5)

    # S: Historical backlink stability (active / total)
    S = min(1.0, active_bl / max(1, total_bl))

    # G: Recent 30-day backlink growth score
    recent_30d = (
        db.query(func.count(Backlink.id))
        .filter(
            Backlink.target_domain == clean,
            Backlink.first_discovered_at >= now - timedelta(days=30),
        )
        .scalar()
        or 0
    )
    G = min(1.0, math.log1p(recent_30d) / math.log1p(max(5, total_bl)))

    las_value = round(100.0 * (w["R"] * R + w["Q"] * Q + w["D"] * D + w["S"] * S + w["G"] * G), 2)
    confidence = "high" if unique_ref >= 50 else "medium" if unique_ref >= 10 else "low"

    record = AuthorityScore(
        domain=clean,
        las_score=las_value,
        r_component=round(R, 4),
        q_component=round(Q, 4),
        d_component=round(D, 4),
        s_component=round(S, 4),
        g_component=round(G, 4),
        formula_version="LAS-v1.0-experimental",
        confidence_level=confidence,
        data_coverage=data_coverage,
        calculated_at=now,
    )
    db.add(record)
    db.commit()

    return {
        "domain": clean,
        "las_score": las_value,
        "components": {"R": round(R, 4), "Q": round(Q, 4), "D": round(D, 4), "S": round(S, 4), "G": round(G, 4)},
        "weights": w,
        "formula_version": "LAS-v1.0-experimental",
        "confidence_level": confidence,
        "data_coverage": data_coverage,
        "calculated_at": now.isoformat(),
        "label": "Internally calculated experimental metric (Not Moz DA / Ahrefs DR / Semrush AS)",
    }