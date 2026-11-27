from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.session import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    root_domain = Column(String(255), nullable=False, index=True)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TrackedDomain(Base):
    __tablename__ = "tracked_domains"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    https_available = Column(Boolean, default=False)
    http_status = Column(Integer, nullable=True)
    title = Column(String(512), default="")
    meta_description = Column(Text, default="")
    registration_age_days = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SeedDomain(Base):
    __tablename__ = "seed_domains"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    seed_url = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    is_active = Column(Boolean, default=True)
    recrawl_interval_hours = Column(Integer, default=168)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    id = Column(Integer, primary_key=True, index=True)
    seed_domain_id = Column(Integer, ForeignKey("seed_domains.id", ondelete="SET NULL"), nullable=True)
    target_domain = Column(String(255), nullable=False, index=True)
    status = Column(String(50), default="queued", index=True)
    pages_crawled = Column(Integer, default=0)
    links_discovered = Column(Integer, default=0)
    max_pages = Column(Integer, default=10000)
    max_depth = Column(Integer, default=3)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    id = Column(BigInteger, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String(20), default="INFO")
    url = Column(Text, default="")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class DiscoveredUrl(Base):
    __tablename__ = "discovered_urls"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    normalized_url = Column(Text, unique=True, nullable=False)
    depth = Column(Integer, default=0)
    status = Column(String(30), default="pending", index=True)
    next_recrawl_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CrawledPage(Base):
    __tablename__ = "crawled_pages"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    url = Column(Text, unique=True, nullable=False)
    http_status = Column(Integer, nullable=False)
    title = Column(String(512), default="")
    meta_description = Column(Text, default="")
    content_hash = Column(String(64), index=True)
    text_excerpt = Column(Text, default="")
    internal_links_count = Column(Integer, default=0)
    external_links_count = Column(Integer, default=0)
    crawled_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Backlink(Base):
    __tablename__ = "backlinks"
    id = Column(BigInteger, primary_key=True, index=True)
    source_domain = Column(String(255), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    target_domain = Column(String(255), nullable=False, index=True)
    target_url = Column(Text, nullable=False)
    anchor_text = Column(String(512), default="")
    anchor_attributes = Column(JSON, default=dict)
    link_type = Column(String(30), default="text")
    is_dofollow = Column(Boolean, default=True, index=True)
    is_nofollow = Column(Boolean, default=False)
    is_sponsored = Column(Boolean, default=False)
    is_ugc = Column(Boolean, default=False)
    source_http_status = Column(Integer, default=200)
    status = Column(String(30), default="active", index=True)
    placement_context = Column(Text, default="")
    first_discovered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_verified_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint("source_url", "target_url", name="uq_backlink_source_target"),
        Index("idx_bl_target_status", "target_domain", "status"),
        Index("idx_bl_target_dofollow", "target_domain", "is_dofollow"),
    )


class BacklinkHistory(Base):
    __tablename__ = "backlink_history"
    id = Column(BigInteger, primary_key=True, index=True)
    backlink_id = Column(BigInteger, ForeignKey("backlinks.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(30))
    new_status = Column(String(30))
    previous_anchor = Column(String(512))
    new_anchor = Column(String(512))
    previous_rel = Column(String(100))
    new_rel = Column(String(100))
    http_status = Column(Integer)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ReferringDomain(Base):
    __tablename__ = "referring_domains"
    id = Column(BigInteger, primary_key=True, index=True)
    target_domain = Column(String(255), nullable=False, index=True)
    source_domain = Column(String(255), nullable=False, index=True)
    total_backlinks = Column(Integer, default=1)
    dofollow_backlinks = Column(Integer, default=0)
    nofollow_backlinks = Column(Integer, default=0)
    status = Column(String(30), default="active")
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("target_domain", "source_domain", name="uq_ref_target_source"),
    )


class DomainMetric(Base):
    __tablename__ = "domain_metrics"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    indexed_pages = Column(Integer, default=0)
    total_backlinks = Column(Integer, default=0)
    unique_referring_domains = Column(Integer, default=0)
    dofollow_count = Column(Integer, default=0)
    nofollow_count = Column(Integer, default=0)
    sponsored_count = Column(Integer, default=0)
    ugc_count = Column(Integer, default=0)
    active_count = Column(Integer, default=0)
    lost_count = Column(Integer, default=0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AuthorityScore(Base):
    __tablename__ = "authority_scores"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    las_score = Column(Float, nullable=True)
    r_component = Column(Float, default=0.0)
    q_component = Column(Float, default=0.0)
    d_component = Column(Float, default=0.0)
    s_component = Column(Float, default=0.0)
    g_component = Column(Float, default=0.0)
    formula_version = Column(String(30), default="LAS-v1.0-experimental")
    confidence_level = Column(String(30), default="insufficient_data")
    data_coverage = Column(Float, default=0.0)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class PageRankResult(Base):
    __tablename__ = "pagerank_results"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    page_url = Column(Text, nullable=True)
    pagerank_score = Column(Float, default=0.0)
    damping_factor = Column(Float, default=0.85)
    iterations = Column(Integer, default=0)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    version_tag = Column(String(50), unique=True, nullable=False)
    artifact_path = Column(Text, nullable=False)
    metrics_json = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now())


class MlPrediction(Base):
    __tablename__ = "ml_predictions"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    backlink_id = Column(BigInteger, ForeignKey("backlinks.id", ondelete="CASCADE"), nullable=True)
    model_version = Column(String(50), default="rule-based-v1")
    spam_probability = Column(Float, nullable=True)
    risk_category = Column(String(50), default="unassessed")
    anomaly_flag = Column(Boolean, default=False)
    cluster_id = Column(Integer, nullable=True)
    supporting_indicators = Column(JSON, default=list)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())


class MlTrainingLabel(Base):
    __tablename__ = "ml_training_labels"
    id = Column(BigInteger, primary_key=True, index=True)
    backlink_id = Column(BigInteger, ForeignKey("backlinks.id", ondelete="CASCADE"), nullable=False)
    is_spam = Column(Boolean, nullable=False)
    reviewer_note = Column(Text, default="")
    labeled_at = Column(DateTime(timezone=True), server_default=func.now())


class AiAnalysis(Base):
    __tablename__ = "ai_analysis"
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)
    model_used = Column(String(100), nullable=False)
    structured_output = Column(JSON, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    disclaimer = Column(String(255), default="AI-generated assessment based on indexed crawl data.")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorDomain(Base):
    __tablename__ = "competitor_domains"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    competitor_domain = Column(String(255), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())