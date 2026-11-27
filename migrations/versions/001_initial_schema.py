"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2026-11-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("root_domain", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_root_domain", "projects", ["root_domain"])

    op.create_table(
        "tracked_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("https_available", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(512), server_default=""),
        sa.Column("meta_description", sa.Text(), server_default=""),
        sa.Column("registration_age_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("domain", name="uq_tracked_domains_domain"),
    )
    op.create_index("ix_tracked_domains_id", "tracked_domains", ["id"])
    op.create_index("ix_tracked_domains_domain", "tracked_domains", ["domain"])

    op.create_table(
        "seed_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("seed_url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), server_default="general"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("recrawl_interval_hours", sa.Integer(), server_default=sa.text("168")),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("domain", name="uq_seed_domains_domain"),
    )
    op.create_index("ix_seed_domains_id", "seed_domains", ["id"])
    op.create_index("ix_seed_domains_domain", "seed_domains", ["domain"])

    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seed_domain_id", sa.Integer(), sa.ForeignKey("seed_domains.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_domain", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="queued"),
        sa.Column("pages_crawled", sa.Integer(), server_default=sa.text("0")),
        sa.Column("links_discovered", sa.Integer(), server_default=sa.text("0")),
        sa.Column("max_pages", sa.Integer(), server_default=sa.text("10000")),
        sa.Column("max_depth", sa.Integer(), server_default=sa.text("3")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_crawl_jobs_id", "crawl_jobs", ["id"])
    op.create_index("ix_crawl_jobs_target_domain", "crawl_jobs", ["target_domain"])
    op.create_index("ix_crawl_jobs_status", "crawl_jobs", ["status"])

    op.create_table(
        "crawl_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.String(20), server_default="INFO"),
        sa.Column("url", sa.Text(), server_default=""),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_crawl_logs_id", "crawl_logs", ["id"])
    op.create_index("ix_crawl_logs_job_id", "crawl_logs", ["job_id"])
    op.create_index("ix_crawl_logs_created_at", "crawl_logs", ["created_at"])

    op.create_table(
        "discovered_urls",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), server_default=sa.text("0")),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("next_recrawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("normalized_url", name="uq_discovered_urls_url"),
    )
    op.create_index("ix_discovered_urls_id", "discovered_urls", ["id"])
    op.create_index("ix_discovered_urls_domain", "discovered_urls", ["domain"])
    op.create_index("ix_discovered_urls_status", "discovered_urls", ["status"])
    op.create_index("ix_discovered_urls_next_recrawl_at", "discovered_urls", ["next_recrawl_at"])

    op.create_table(
        "crawled_pages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), server_default=""),
        sa.Column("meta_description", sa.Text(), server_default=""),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("text_excerpt", sa.Text(), server_default=""),
        sa.Column("internal_links_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("external_links_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("crawled_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("url", name="uq_crawled_pages_url"),
    )
    op.create_index("ix_crawled_pages_id", "crawled_pages", ["id"])
    op.create_index("ix_crawled_pages_domain", "crawled_pages", ["domain"])
    op.create_index("ix_crawled_pages_content_hash", "crawled_pages", ["content_hash"])
    op.create_index("ix_crawled_pages_crawled_at", "crawled_pages", ["crawled_at"])

    op.create_table(
        "backlinks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_domain", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("target_domain", sa.String(255), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("anchor_text", sa.String(512), server_default=""),
        sa.Column("anchor_attributes", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("link_type", sa.String(30), server_default="text"),
        sa.Column("is_dofollow", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_nofollow", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_sponsored", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_ugc", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("source_http_status", sa.Integer(), server_default=sa.text("200")),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("placement_context", sa.Text(), server_default=""),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source_url", "target_url", name="uq_backlink_source_target"),
    )
    op.create_index("ix_backlinks_id", "backlinks", ["id"])
    op.create_index("ix_backlinks_source_domain", "backlinks", ["source_domain"])
    op.create_index("ix_backlinks_target_domain", "backlinks", ["target_domain"])
    op.create_index("ix_backlinks_status", "backlinks", ["status"])
    op.create_index("ix_backlinks_is_dofollow", "backlinks", ["is_dofollow"])
    op.create_index("ix_backlinks_first_discovered_at", "backlinks", ["first_discovered_at"])
    op.create_index("ix_backlinks_last_verified_at", "backlinks", ["last_verified_at"])
    op.create_index("idx_bl_target_status", "backlinks", ["target_domain", "status"])
    op.create_index("idx_bl_target_dofollow", "backlinks", ["target_domain", "is_dofollow"])

    op.create_table(
        "backlink_history",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("backlink_id", sa.BigInteger(), sa.ForeignKey("backlinks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=True),
        sa.Column("previous_anchor", sa.String(512), nullable=True),
        sa.Column("new_anchor", sa.String(512), nullable=True),
        sa.Column("previous_rel", sa.String(100), nullable=True),
        sa.Column("new_rel", sa.String(100), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_backlink_history_id", "backlink_history", ["id"])
    op.create_index("ix_backlink_history_backlink_id", "backlink_history", ["backlink_id"])
    op.create_index("ix_backlink_history_recorded_at", "backlink_history", ["recorded_at"])

    op.create_table(
        "referring_domains",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("target_domain", sa.String(255), nullable=False),
        sa.Column("source_domain", sa.String(255), nullable=False),
        sa.Column("total_backlinks", sa.Integer(), server_default=sa.text("1")),
        sa.Column("dofollow_backlinks", sa.Integer(), server_default=sa.text("0")),
        sa.Column("nofollow_backlinks", sa.Integer(), server_default=sa.text("0")),
        sa.Column("status", sa.String(30), server_default="active"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("target_domain", "source_domain", name="uq_ref_target_source"),
    )
    op.create_index("ix_referring_domains_id", "referring_domains", ["id"])
    op.create_index("ix_referring_domains_target_domain", "referring_domains", ["target_domain"])
    op.create_index("ix_referring_domains_source_domain", "referring_domains", ["source_domain"])

    op.create_table(
        "domain_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("indexed_pages", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_backlinks", sa.Integer(), server_default=sa.text("0")),
        sa.Column("unique_referring_domains", sa.Integer(), server_default=sa.text("0")),
        sa.Column("dofollow_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("nofollow_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("sponsored_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("ugc_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("active_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("lost_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_domain_metrics_id", "domain_metrics", ["id"])
    op.create_index("ix_domain_metrics_domain", "domain_metrics", ["domain"])
    op.create_index("ix_domain_metrics_recorded_at", "domain_metrics", ["recorded_at"])

    op.create_table(
        "authority_scores",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("las_score", sa.Float(), nullable=True),
        sa.Column("r_component", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("q_component", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("d_component", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("s_component", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("g_component", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("formula_version", sa.String(30), server_default="LAS-v1.0-experimental"),
        sa.Column("confidence_level", sa.String(30), server_default="insufficient_data"),
        sa.Column("data_coverage", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_authority_scores_id", "authority_scores", ["id"])
    op.create_index("ix_authority_scores_domain", "authority_scores", ["domain"])
    op.create_index("ix_authority_scores_calculated_at", "authority_scores", ["calculated_at"])

    op.create_table(
        "pagerank_results",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("page_url", sa.Text(), nullable=True),
        sa.Column("pagerank_score", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("damping_factor", sa.Float(), server_default=sa.text("0.85")),
        sa.Column("iterations", sa.Integer(), server_default=sa.text("0")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_pagerank_results_id", "pagerank_results", ["id"])
    op.create_index("ix_pagerank_results_domain", "pagerank_results", ["domain"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("version_tag", sa.String(50), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("version_tag", name="uq_model_versions_tag"),
    )
    op.create_index("ix_model_versions_id", "model_versions", ["id"])

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("backlink_id", sa.BigInteger(), sa.ForeignKey("backlinks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("model_version", sa.String(50), server_default="rule-based-v1"),
        sa.Column("spam_probability", sa.Float(), nullable=True),
        sa.Column("risk_category", sa.String(50), server_default="unassessed"),
        sa.Column("anomaly_flag", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("supporting_indicators", sa.JSON(), server_default=sa.text("'[]'")),
        sa.Column("predicted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ml_predictions_id", "ml_predictions", ["id"])
    op.create_index("ix_ml_predictions_domain", "ml_predictions", ["domain"])

    op.create_table(
        "ml_training_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("backlink_id", sa.BigInteger(), sa.ForeignKey("backlinks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_spam", sa.Boolean(), nullable=False),
        sa.Column("reviewer_note", sa.Text(), server_default=""),
        sa.Column("labeled_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ml_training_labels_id", "ml_training_labels", ["id"])

    op.create_table(
        "ai_analysis",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("structured_output", sa.JSON(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0")),
        sa.Column("disclaimer", sa.String(255), server_default="AI-generated assessment based on indexed crawl data."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_analysis_id", "ai_analysis", ["id"])
    op.create_index("ix_ai_analysis_domain", "ai_analysis", ["domain"])

    op.create_table(
        "competitor_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("competitor_domain", sa.String(255), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_competitor_domains_id", "competitor_domains", ["id"])


def downgrade() -> None:
    for table in [
        "competitor_domains", "ai_analysis", "ml_training_labels", "ml_predictions",
        "model_versions", "pagerank_results", "authority_scores", "domain_metrics",
        "referring_domains", "backlink_history", "backlinks", "crawled_pages",
        "discovered_urls", "crawl_logs", "crawl_jobs", "seed_domains",
        "tracked_domains", "projects", "users",
    ]:
        op.drop_table(table)
