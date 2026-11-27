import json
import subprocess
import sys


def run_spider_subprocess(job_id: int, seed_urls: list[str], max_pages: int = 1000, max_depth: int = 3) -> int:
    """Executes Scrapy spider in a fresh child process to keep Celery worker RAM low and clean."""
    code = (
        "import json, sys; "
        "from scrapy.crawler import CrawlerProcess; "
        "from app.crawler.seo_spider import SeoIntelligenceSpider; "
        "args = json.loads(sys.argv[1]); "
        "proc = CrawlerProcess(); "
        "proc.crawl(SeoIntelligenceSpider, **args); "
        "proc.start()"
    )
    payload = json.dumps({
        "job_id": job_id,
        "seed_urls": seed_urls,
        "max_pages": max_pages,
        "max_depth": max_depth,
    })
    res = subprocess.run([sys.executable, "-c", code, payload], check=False)
    return res.returncode