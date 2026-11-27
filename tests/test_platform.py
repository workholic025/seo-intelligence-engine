import pytest
from fastapi.testclient import TestClient

from app.ai.deepseek_service import AiSeoAssessmentSchema
from app.core.auth import (
    create_access_token,
    hash_password,
    verify_password,
    _decode_token,
)
from app.core.security import validate_safe_external_url
from app.crawler.seo_spider import normalize_url
from app.main import app

client = TestClient(app)


# ── SSRF Protection ───────────────────────────────────────────────────────────

def test_ssrf_blocks_localhost_and_private_ranges():
    for bad in [
        "http://127.0.0.1:8000/admin",
        "http://localhost/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/",
        "file:///etc/passwd",
    ]:
        with pytest.raises(ValueError):
            validate_safe_external_url(bad)


def test_ssrf_accepts_public_url():
    # Only DNS-resolvable public URLs pass; use a known stable hostname
    url = validate_safe_external_url("https://example.com")
    assert url.startswith("https://")


# ── URL Normalization ─────────────────────────────────────────────────────────

def test_url_normalization_strips_tracking_params():
    u1 = normalize_url("HTTPS://Example.COM/page/?utm_source=x&b=2&a=1#top")
    u2 = normalize_url("https://example.com/page?a=1&b=2")
    assert u1 == u2


def test_url_normalization_lowercases_scheme_and_host():
    u = normalize_url("HTTPS://WWW.EXAMPLE.COM/Path")
    assert u.startswith("https://www.example.com/")


def test_url_normalization_removes_fragment():
    u = normalize_url("https://example.com/page#section")
    assert "#" not in u


# ── Password Hashing ──────────────────────────────────────────────────────────

def test_password_hash_is_not_plaintext():
    hashed = hash_password("MySecretPass1!")
    assert hashed != "MySecretPass1!"
    assert hashed.startswith("pbkdf2:sha256:")


def test_password_verify_correct():
    pw = "CorrectHorseBattery9"
    assert verify_password(pw, hash_password(pw)) is True


def test_password_verify_wrong():
    hashed = hash_password("rightpassword")
    assert verify_password("wrongpassword", hashed) is False


def test_password_hashes_are_unique():
    pw = "SamePassword1"
    assert hash_password(pw) != hash_password(pw)  # different salts


# ── JWT Token ─────────────────────────────────────────────────────────────────

def test_token_roundtrip():
    token = create_access_token(user_id=42, email="test@seo.local")
    payload = _decode_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "test@seo.local"
    assert "exp" in payload


def test_token_has_three_parts():
    token = create_access_token(user_id=1, email="a@b.com")
    assert token.count(".") == 2


def test_tampered_token_raises():
    token = create_access_token(user_id=1, email="a@b.com")
    parts = token.split(".")
    parts[1] = parts[1][:-2] + "XX"  # corrupt payload
    with pytest.raises(ValueError):
        _decode_token(".".join(parts))


# ── AI Schema Validation ──────────────────────────────────────────────────────

def test_ai_pydantic_schema_validation():
    payload = {
        "summary": "Indexed profile shows 12 active backlinks.",
        "topical_relevance_assessment": "Moderate topical overlap.",
        "anchor_diversity_observation": "Balanced branded and generic anchors.",
        "quality_indicators": ["Contextual placements"],
        "risk_indicators": [],
        "recommendations": ["Expand referring domain diversity"],
    }
    parsed = AiSeoAssessmentSchema.model_validate(payload)
    assert "assessment" in parsed.evidence_disclaimer.lower()


def test_ai_schema_requires_summary():
    with pytest.raises(Exception):
        AiSeoAssessmentSchema.model_validate({"topical_relevance_assessment": "x"})


# ── API Endpoints ─────────────────────────────────────────────────────────────

def test_health_endpoint():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_dashboard_stats_returns_expected_keys():
    r = client.get("/api/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    for key in ("total_backlinks", "referring_domains", "active_backlinks", "total_indexed_pages"):
        assert key in data, f"Missing key: {key}"


def test_domain_overview_returns_metric_source():
    r = client.get("/api/domains/example.com/overview")
    assert r.status_code == 200
    assert r.json()["metric_source"] == "internal_local_index"


def test_domain_backlinks_pagination():
    r = client.get("/api/domains/example.com/backlinks", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    data = r.json()
    assert "total" in data and "items" in data
    assert len(data["items"]) <= 10


def test_domain_backlinks_invalid_page_rejected():
    r = client.get("/api/domains/example.com/backlinks", params={"page": 0})
    assert r.status_code == 422


def test_competitors_compare_requires_at_least_two_domains():
    r = client.get("/api/competitors/compare", params={"domains": "single.com"})
    assert r.status_code == 400


def test_competitors_compare_caps_at_five():
    domains = "a.com,b.com,c.com,d.com,e.com,f.com,g.com"
    r = client.get("/api/competitors/compare", params={"domains": domains})
    # Either OK with ≤5 domains used, or 400 — must not 500
    assert r.status_code in (200, 400)


def test_crawler_start_rejects_private_ip():
    r = client.post("/api/crawler/start", json={
        "seed_domains": ["http://192.168.0.1"],
        "max_pages": 50,
        "max_depth": 1,
    })
    assert r.status_code == 400


def test_auth_register_and_login(tmp_path):
    # Register a new user
    reg = client.post("/api/auth/register", json={
        "email": "pytest_user@seo.local",
        "full_name": "Pytest User",
        "password": "TestPass1234",
    })
    # Accept 201 (created) or 409 (already exists from prior test run)
    assert reg.status_code in (201, 409)

    # Login
    login = client.post("/api/auth/login", json={
        "email": "pytest_user@seo.local",
        "password": "TestPass1234",
    })
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_auth_login_wrong_password():
    r = client.post("/api/auth/login", json={
        "email": "pytest_user@seo.local",
        "password": "wrongpassword",
    })
    assert r.status_code == 401


def test_auth_me_requires_token():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_csv_export_returns_csv_content_type():
    r = client.get("/api/export/backlinks", params={"domain": "example.com"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
