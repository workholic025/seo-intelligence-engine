import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import scrapy
import tldextract
from bs4 import BeautifulSoup
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.security import validate_safe_external_url
from app.database.session import SessionLocal
from app.models.models import (
    Backlink,
    CrawledPage,
    CrawlJob,
    CrawlLog,
    DiscoveredUrl,
    ReferringDomain,
    TrackedDomain,
)


def normalize_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    clean_query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=False)
            if not k.lower().startswith(("utm_", "fbclid", "gclid", "ref"))
        )
    )
    return urlunparse((scheme, netloc, path, "", clean_query, ""))


def extract_root_domain(url_or_host: str) -> str:
    ext = tldextract.extract(url_or_host)
    if not ext.domain or not ext.suffix:
        return ""
    return f"{ext.domain}.{ext.suffix}".lower()


class SeoIntelligenceSpider(scrapy.Spider):
    name = "seo_intelligence"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": settings.CRAWLER_CONCURRENCY,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": settings.CRAWLER_DOWNLOAD_DELAY,
        "DOWNLOAD_TIMEOUT": 15,
        "RETRY_TIMES": 2,
        "DOWNLOAD_MAXSIZE": settings.CRAWLER_MAX_RESPONSE_BYTES,
        "DEPTH_LIMIT": settings.CRAWLER_MAX_DEPTH,
        "DEPTH_PRIORITY": 1,  # Enables Breadth-First Search (BFS)
        "SCHEDULER_DISK_QUEUE": "scrapy.squeues.PickleFifoDiskQueue",
        "SCHEDULER_MEMORY_QUEUE": "scrapy.squeues.FifoMemoryQueue",
        "COOKIES_ENABLED": False,
        "USER_AGENT": "SEOIntelligenceBot/1.0 (+http://localhost:8000/docs)",
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, job_id: int, seed_urls: list[str], max_pages: int = 1000, max_depth: int = 3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = int(job_id)
        self.max_pages = int(max_pages)
        self.max_depth = int(max_depth)
        self.pages_processed = 0
        self.links_discovered = 0
        self.seed_urls = seed_urls
        self.allowed_domains = list({extract_root_domain(u) for u in seed_urls if extract_root_domain(u)})
        self.db = SessionLocal()

    def start_requests(self):
        job = self.db.query(CrawlJob).filter(CrawlJob.id == self.job_id).first()
        if job:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            self.db.commit()

        for raw in self.seed_urls:
            try:
                safe_url = validate_safe_external_url(raw)
                norm = normalize_url(safe_url)
            except ValueError as exc:
                self._log("WARNING", raw, f"Blocked seed URL: {exc}")
                continue

            # Queue homepage
            yield scrapy.Request(norm, callback=self.parse_page, errback=self.handle_error, meta={"depth": 0})
            # Queue sitemap discovery
            parsed = urlparse(norm)
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            yield scrapy.Request(sitemap_url, callback=self.parse_sitemap, errback=self.ignore_error, dont_filter=True)

    def parse_sitemap(self, response):
        if response.status != 200 or self.pages_processed >= self.max_pages:
            return
        try:
            root = ET.fromstring(response.body)
        except ET.ParseError:
            return

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        # Handle sitemap index files
        for loc in root.findall(".//sm:sitemap/sm:loc", ns)[:10]:
            if loc.text:
                try:
                    safe = validate_safe_external_url(loc.text.strip())
                    yield scrapy.Request(safe, callback=self.parse_sitemap, errback=self.ignore_error)
                except ValueError:
                    continue

        # Handle URL entries
        for loc in root.findall(".//sm:url/sm:loc", ns)[:200]:
            if not loc.text or self.pages_processed >= self.max_pages:
                break
            try:
                safe = validate_safe_external_url(loc.text.strip())
                norm = normalize_url(safe)
                if extract_root_domain(norm) in self.allowed_domains:
                    yield scrapy.Request(norm, callback=self.parse_page, errback=self.handle_error, meta={"depth": 1})
            except ValueError:
                continue

    def parse_page(self, response):
        if self.pages_processed >= self.max_pages:
            self.crawler.engine.close_spider(self, reason="max_pages_reached")
            return

        # Re-validate final URL after any redirects (SSRF redirect protection)
        try:
            final_url = normalize_url(validate_safe_external_url(response.url))
        except ValueError as exc:
            self._log("WARNING", response.url, f"Blocked redirect target: {exc}")
            return

        ctype = response.headers.get(b"Content-Type", b"").decode("utf-8", errors="ignore").lower()
        if "text/html" not in ctype:
            return

        src_domain = extract_root_domain(final_url)
        if not src_domain:
            return

        soup = BeautifulSoup(response.text, "lxml")
        title = (soup.title.string or "").strip()[:512] if soup.title and soup.title.string else ""
        meta_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
        meta_desc = (meta_tag.get("content") or "").strip()[:1000] if meta_tag else ""

        # Extract visible text for content hashing & TF-IDF topical relevance
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        visible_text = " ".join(soup.get_text(" ", strip=True).split())
        content_hash = hashlib.sha256(visible_text.encode("utf-8", errors="ignore")).hexdigest()
        text_excerpt = visible_text[:4000]

        internal_links = []
        external_links = []
        seen_targets = set()

        for a_tag in soup.find_all("a", href=True):
            href = (a_tag.get("href") or "").strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            abs_url = urljoin(final_url, href).split("#")[0]
            parsed_target = urlparse(abs_url)
            if parsed_target.scheme not in ("http", "https"):
                continue

            norm_target = normalize_url(abs_url)
            tgt_domain = extract_root_domain(norm_target)
            if not tgt_domain:
                continue

            if tgt_domain == src_domain:
                internal_links.append(norm_target)
            elif norm_target not in seen_targets:
                seen_targets.add(norm_target)
                rel_vals = [r.lower() for r in (a_tag.get("rel") or [])]
                is_nofollow = "nofollow" in rel_vals
                is_sponsored = "sponsored" in rel_vals
                is_ugc = "ugc" in rel_vals
                is_dofollow = not (is_nofollow or is_sponsored or is_ugc)

                anchor_text = " ".join(a_tag.get_text(" ", strip=True).split())[:512]
                link_type = "image" if (not anchor_text and a_tag.find("img")) else "text"
                parent_text = " ".join((a_tag.parent.get_text(" ", strip=True) if a_tag.parent else "").split())[:350]

                external_links.append({
                    "source_domain": src_domain,
                    "source_url": final_url,
                    "target_domain": tgt_domain,
                    "target_url": norm_target,
                    "anchor_text": anchor_text,
                    "anchor_attributes": {"rel": rel_vals, "target": a_tag.get("target")},
                    "link_type": link_type,
                    "is_dofollow": is_dofollow,
                    "is_nofollow": is_nofollow,
                    "is_sponsored": is_sponsored,
                    "is_ugc": is_ugc,
                    "source_http_status": response.status,
                    "status": "active",
                    "placement_context": parent_text,
                })

        self._persist_page_and_links(
            src_domain=src_domain,
            final_url=final_url,
            http_status=response.status,
            title=title,
            meta_desc=meta_desc,
            content_hash=content_hash,
            text_excerpt=text_excerpt,
            internal_count=len(internal_links),
            external_links=external_links,
        )

        self.pages_processed += 1
        self.links_discovered += len(external_links)
        if self.pages_processed % 5 == 0:
            self._update_job_progress()

        # Enqueue internal BFS links up to max_depth
        cur_depth = response.meta.get("depth", 0)
        if cur_depth < self.max_depth:
            for link in internal_links[:40]:
                yield scrapy.Request(link, callback=self.parse_page, errback=self.handle_error, meta={"depth": cur_depth + 1})

    def _persist_page_and_links(
        self,
        src_domain: str,
        final_url: str,
        http_status: int,
        title: str,
        meta_desc: str,
        content_hash: str,
        text_excerpt: str,
        internal_count: int,
        external_links: list[dict],
    ) -> None:
        now = datetime.now(timezone.utc)
        try:
            # Upsert CrawledPage
            existing_page = self.db.query(CrawledPage).filter(CrawledPage.url == final_url).first()
            if existing_page:
                existing_page.http_status = http_status
                existing_page.title = title
                existing_page.meta_description = meta_desc
                existing_page.content_hash = content_hash
                existing_page.text_excerpt = text_excerpt
                existing_page.internal_links_count = internal_count
                existing_page.external_links_count = len(external_links)
                existing_page.crawled_at = now
            else:
                self.db.add(
                    CrawledPage(
                        domain=src_domain,
                        url=final_url,
                        http_status=http_status,
                        title=title,
                        meta_description=meta_desc,
                        content_hash=content_hash,
                        text_excerpt=text_excerpt,
                        internal_links_count=internal_count,
                        external_links_count=len(external_links),
                    )
                )

            # Update TrackedDomain metadata if homepage
            if urlparse(final_url).path in ("", "/"):
                td = self.db.query(TrackedDomain).filter(TrackedDomain.domain == src_domain).first()
                if not td:
                    td = TrackedDomain(domain=src_domain)
                    self.db.add(td)
                td.http_status = http_status
                td.https_available = final_url.startswith("https://")
                td.title = title
                td.meta_description = meta_desc

            # Mark DiscoveredUrl as crawled and schedule weekly recrawl
            stmt_url = pg_insert(DiscoveredUrl).values(
                domain=src_domain,
                normalized_url=final_url,
                status="crawled",
                next_recrawl_at=now + timedelta(days=7),
            ).on_conflict_do_update(
                index_elements=["normalized_url"],
                set_={"status": "crawled", "next_recrawl_at": now + timedelta(days=7)},
            )
            self.db.execute(stmt_url)

            # Bulk Upsert Backlinks & ReferringDomains
            ref_counts: dict[str, list[int]] = {}
            for bl in external_links:
                stmt_bl = pg_insert(Backlink).values(**bl, last_verified_at=now).on_conflict_do_update(
                    constraint="uq_backlink_source_target",
                    set_={
                        "anchor_text": bl["anchor_text"],
                        "is_dofollow": bl["is_dofollow"],
                        "is_nofollow": bl["is_nofollow"],
                        "is_sponsored": bl["is_sponsored"],
                        "is_ugc": bl["is_ugc"],
                        "source_http_status": http_status,
                        "status": "active",
                        "placement_context": bl["placement_context"],
                        "last_verified_at": now,
                    },
                )
                self.db.execute(stmt_bl)
                t_dom = bl["target_domain"]
                if t_dom not in ref_counts:
                    ref_counts[t_dom] = [0, 0, 0]
                ref_counts[t_dom][0] += 1
                ref_counts[t_dom][1] += 1 if bl["is_dofollow"] else 0
                ref_counts[t_dom][2] += 1 if bl["is_nofollow"] else 0

            for tgt_dom, (tot, do_c, no_c) in ref_counts.items():
                stmt_ref = pg_insert(ReferringDomain).values(
                    target_domain=tgt_dom,
                    source_domain=src_domain,
                    total_backlinks=tot,
                    dofollow_backlinks=do_c,
                    nofollow_backlinks=no_c,
                    status="active",
                    last_seen_at=now,
                ).on_conflict_do_update(
                    constraint="uq_ref_target_source",
                    set_={"last_seen_at": now, "status": "active"},
                )
                self.db.execute(stmt_ref)

            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            self._log("ERROR", final_url, f"DB persist failed: {exc}")

    def _update_job_progress(self) -> None:
        job = self.db.query(CrawlJob).filter(CrawlJob.id == self.job_id).first()
        if job:
            if job.status == "stopped":
                self.crawler.engine.close_spider(self, reason="stopped_by_user")
                return
            job.pages_crawled = self.pages_processed
            job.links_discovered = self.links_discovered
            self.db.commit()

    def _log(self, level: str, url: str, message: str) -> None:
        try:
            self.db.add(CrawlLog(job_id=self.job_id, level=level, url=url[:1000], message=message[:1000]))
            self.db.commit()
        except Exception:
            self.db.rollback()

    def handle_error(self, failure):
        self._log("WARNING", failure.request.url, str(failure.value))

    def ignore_error(self, failure):
        pass

    def closed(self, reason):
        job = self.db.query(CrawlJob).filter(CrawlJob.id == self.job_id).first()
        if job and job.status != "stopped":
            job.status = "completed" if reason in ("finished", "max_pages_reached") else "failed"
            job.pages_crawled = self.pages_processed
            job.links_discovered = self.links_discovered
            job.finished_at = datetime.now(timezone.utc)
            self.db.commit()
        self.db.close()