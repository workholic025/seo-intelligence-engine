import ipaddress
import socket
from urllib.parse import urlparse


BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}


def validate_safe_external_url(raw_url: str) -> str:
    """
    Validates URL scheme and resolves DNS to block SSRF attacks against
    localhost, private LAN ranges, link-local cloud metadata (169.254.169.254), etc.
    """
    candidate = raw_url.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Invalid URL or unsupported scheme. Only http/https allowed.")

    hostname = parsed.hostname.lower()
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Access to local or internal hostnames is blocked by SSRF policy.")

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for domain: {hostname}") from exc

    for info in addr_infos:
        ip_str = info[4][0]
        ip_obj = ipaddress.ip_address(ip_str)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
        ):
            raise ValueError(f"Blocked non-public IP address ({ip_str}) for {hostname}.")

    return candidate