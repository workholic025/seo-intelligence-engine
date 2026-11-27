from urllib.parse import urlparse

from app.core.security import validate_safe_external_url


def clean_host(raw: str) -> str:
    safe_url = validate_safe_external_url(raw)
    host = urlparse(safe_url).hostname or ""
    return host.removeprefix("www.").lower()
