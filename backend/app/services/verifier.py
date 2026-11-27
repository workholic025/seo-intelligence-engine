from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.security import validate_safe_external_url
from app.crawler.seo_spider import normalize_url
from app.models.models import Backlink, BacklinkHistory

_MAX_WORKERS = 10
_HEADERS = {"User-Agent": "SEOIntelligenceVerifier/1.0 (+http://localhost:8000/docs)"}


def _fetch_one(bl_id: int, source_url: str, target_url: str) -> dict:
    """Pure HTTP worker — no DB access. Returns a result dict for the main thread."""
    result = {"bl_id": bl_id, "error": None, "http_status": 0, "final_url": source_url, "redirected": False, "html": None}
    try:
        safe_src = validate_safe_external_url(source_url)
        with httpx.Client(timeout=12.0, follow_redirects=True, headers=_HEADERS) as client:
            resp = client.get(safe_src)
            validate_safe_external_url(str(resp.url))
            result["http_status"] = resp.status_code
            result["final_url"] = str(resp.url)
            result["redirected"] = len(resp.history) > 0 and str(resp.url) != source_url
            result["html"] = resp.text if resp.status_code < 400 else None
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
        result["error"] = "network"
    except ValueError:
        result["error"] = "ssrf"
    return result


def _apply_result(db: Session, bl: Backlink, fetch: dict, now: datetime) -> str:
    """Apply the HTTP fetch result to the Backlink ORM object and return the new status."""
    prev_status = bl.status
    prev_anchor = bl.anchor_text
    prev_rel = ",".join((bl.anchor_attributes or {}).get("rel", []))

    if fetch["error"] == "network":
        bl.status = "temp_unavailable"
        bl.last_verified_at = now
        _record_history(db, bl, prev_status, "temp_unavailable", prev_anchor, bl.anchor_text, prev_rel, prev_rel, 0)
        return "temp_unavailable"

    if fetch["error"] == "ssrf":
        bl.status = "not_verified"
        bl.last_verified_at = now
        return "not_verified"

    http_status = fetch["http_status"]
    bl.source_http_status = http_status
    bl.last_verified_at = now

    if http_status >= 500 or http_status == 429:
        bl.status = "temp_unavailable"
        _record_history(db, bl, prev_status, "temp_unavailable", prev_anchor, bl.anchor_text, prev_rel, prev_rel, http_status)
        return "temp_unavailable"

    if http_status in (404, 410):
        bl.status = "lost"
        _record_history(db, bl, prev_status, "lost", prev_anchor, bl.anchor_text, prev_rel, prev_rel, http_status)
        return "lost"

    if not fetch["html"]:
        new_status = "redirected" if fetch["redirected"] else "lost"
        bl.status = new_status
        _record_history(db, bl, prev_status, new_status, prev_anchor, bl.anchor_text, prev_rel, prev_rel, http_status)
        return new_status

    soup = BeautifulSoup(fetch["html"], "lxml")
    found_tag = None
    expected_norm = normalize_url(bl.target_url)

    for a in soup.find_all("a", href=True):
        candidate = normalize_url(urljoin(fetch["final_url"], a["href"].split("#")[0]))
        if candidate == expected_norm:
            found_tag = a
            break

    if not found_tag:
        new_status = "redirected" if fetch["redirected"] else "lost"
        bl.status = new_status
        _record_history(db, bl, prev_status, new_status, prev_anchor, bl.anchor_text, prev_rel, prev_rel, http_status)
        return new_status

    rel_vals = [r.lower() for r in (found_tag.get("rel") or [])]
    new_rel = ",".join(rel_vals)
    new_anchor = " ".join(found_tag.get_text(" ", strip=True).split())[:512]
    bl.anchor_text = new_anchor
    bl.anchor_attributes = {"rel": rel_vals, "target": found_tag.get("target")}
    bl.is_nofollow = "nofollow" in rel_vals
    bl.is_sponsored = "sponsored" in rel_vals
    bl.is_ugc = "ugc" in rel_vals
    bl.is_dofollow = not (bl.is_nofollow or bl.is_sponsored or bl.is_ugc)
    bl.status = "active"

    if prev_status != "active" or prev_anchor != new_anchor or prev_rel != new_rel:
        _record_history(db, bl, prev_status, "active", prev_anchor, new_anchor, prev_rel, new_rel, http_status)

    return "active"


def verify_backlinks_batch(db: Session, target_domain: str | None = None, batch_size: int = 50) -> dict:
    q = db.query(Backlink).order_by(Backlink.last_verified_at.asc())
    if target_domain:
        q = q.filter(Backlink.target_domain == target_domain.lower().strip())
    records = q.limit(batch_size).all()

    if not records:
        return {"checked": 0, "active": 0, "lost": 0, "temp_unavailable": 0, "redirected": 0}

    # Submit all HTTP fetches in parallel (pure functions — no DB access in threads)
    futures = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for bl in records:
            fut = pool.submit(_fetch_one, bl.id, bl.source_url, bl.target_url)
            futures[fut] = bl.id

    fetch_map: dict[int, dict] = {}
    for fut in as_completed(futures):
        result = fut.result()
        fetch_map[result["bl_id"]] = result

    # Apply results sequentially in the main thread (safe DB access)
    summary = {"checked": 0, "active": 0, "lost": 0, "temp_unavailable": 0, "redirected": 0}
    now = datetime.now(timezone.utc)
    id_map = {bl.id: bl for bl in records}

    for bl_id, fetch in fetch_map.items():
        bl = id_map[bl_id]
        new_status = _apply_result(db, bl, fetch, now)
        summary["checked"] += 1
        if new_status in summary:
            summary[new_status] += 1

    db.commit()
    return summary


def _record_history(
    db: Session,
    bl: Backlink,
    prev_status: str,
    new_status: str,
    prev_anchor: str,
    new_anchor: str,
    prev_rel: str,
    new_rel: str,
    http_status: int,
) -> None:
    db.add(
        BacklinkHistory(
            backlink_id=bl.id,
            previous_status=prev_status,
            new_status=new_status,
            previous_anchor=prev_anchor,
            new_anchor=new_anchor,
            previous_rel=prev_rel,
            new_rel=new_rel,
            http_status=http_status,
        )
    )
