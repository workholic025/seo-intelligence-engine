from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.ai.deepseek_service import run_deepseek_analysis
from app.algorithms.engine import analyze_anchor_texts
from app.database.session import get_db
from app.models.models import AiAnalysis, Backlink
from app.schemas import AiAnalyzeRequest
from app.services.domain_service import get_overview

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/analyze")
async def ai_analyze(payload: AiAnalyzeRequest, db: Session = Depends(get_db)):
    clean = payload.domain.removeprefix("www.").lower().strip()
    overview = get_overview(clean, db)
    anchors = analyze_anchor_texts(db, clean)
    sample_links = (
        db.query(Backlink.source_domain, Backlink.anchor_text, Backlink.is_dofollow, Backlink.placement_context)
        .filter(Backlink.target_domain == clean)
        .limit(15)
        .all()
    )
    context = {
        "overview": overview,
        "anchor_distribution": anchors["distribution"],
        "sample_backlinks": [
            {"source": s, "anchor": a, "dofollow": df, "context": (ctx or "")[:200]}
            for s, a, df, ctx in sample_links
        ],
    }
    return await run_deepseek_analysis(db, clean, payload.analysis_type, context)


@router.get("/reports")
def list_ai_reports(
    domain: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(AiAnalysis).order_by(desc(AiAnalysis.created_at))
    if domain:
        q = q.filter(AiAnalysis.domain == domain.removeprefix("www.").lower().strip())
    rows = q.limit(limit).all()
    return {
        "reports": [
            {
                "id": r.id,
                "domain": r.domain,
                "analysis_type": r.analysis_type,
                "model_used": r.model_used,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "structured_output": r.structured_output,
                "disclaimer": r.disclaimer,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }
