from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    target: str


class CrawlStartRequest(BaseModel):
    seed_domains: list[str] = Field(..., min_length=1, max_length=25)
    max_pages: int = Field(500, ge=10, le=10000)
    max_depth: int = Field(2, ge=1, le=5)


class CrawlStopRequest(BaseModel):
    job_id: int


class AiAnalyzeRequest(BaseModel):
    domain: str
    analysis_type: Literal["backlink_context", "seo_report", "recommendations"] = "seo_report"


class ProjectCreateRequest(BaseModel):
    name: str
    root_domain: str
    description: str = ""


class TrainingLabelRequest(BaseModel):
    backlink_id: int
    is_spam: bool
    reviewer_note: str = ""


class SeedCreateRequest(BaseModel):
    domain: str
    category: str = "general"


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str
