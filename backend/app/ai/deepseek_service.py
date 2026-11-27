import asyncio
import json
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AiAnalysis, Backlink

# Official DeepSeek API list rates per 1M tokens (USD) for rough cost estimation
MODEL_PRICING_PER_1M = {
    "deepseek-flash": {"input": 0.30, "output": 1.20},
    "deepseek-v4-pro": {"input": 1.32, "output": 3.96},
}


class AiSeoAssessmentSchema(BaseModel):
    summary: str = Field(..., description="Concise executive assessment strictly referencing supplied crawl data")
    topical_relevance_assessment: str
    anchor_diversity_observation: str
    quality_indicators: list[str]
    risk_indicators: list[str]
    recommendations: list[str]
    evidence_disclaimer: str = "AI-generated assessment based solely on supplied local index records, not verified third-party facts."


async def run_deepseek_analysis(
    db: Session,
    domain: str,
    analysis_type: Literal["backlink_context", "seo_report", "recommendations"],
    context_payload: dict,
) -> dict:
    if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY == "your_deepseek_api_key_here":
        return {
            "status": "unavailable",
            "error": "DEEPSEEK_API_KEY is not configured in .env.",
        }

    system_prompt = (
        "You are an objective SEO analyst. Analyze ONLY the verified local crawl data provided in the user JSON. "
        "NEVER fabricate backlinks, traffic figures, or Moz/Semrush/Google metrics. "
        "Return valid JSON strictly matching these keys: summary (string), topical_relevance_assessment (string), "
        "anchor_diversity_observation (string), quality_indicators (array of strings), "
        "risk_indicators (array of strings), recommendations (array of strings)."
    )

    body = {
        "model": settings.DEEPSEEK_MODEL or "deepseek-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({"analysis_type": analysis_type, "data": context_payload})[:12000]},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "stream": False,
    }

    url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    last_err = ""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=body)

            if resp.status_code == 429:
                await asyncio.sleep(2 ** attempt)
                last_err = "DeepSeek API rate limit hit."
                continue

            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = AiSeoAssessmentSchema.model_validate_json(raw_content)

            usage = data.get("usage", {})
            p_tokens = int(usage.get("prompt_tokens", 0))
            c_tokens = int(usage.get("completion_tokens", 0))
            model_used = data.get("model", body["model"])

            rates = MODEL_PRICING_PER_1M.get(body["model"], {"input": 0.30, "output": 1.20})
            est_cost_usd = round((p_tokens / 1e6) * rates["input"] + (c_tokens / 1e6) * rates["output"], 6)

            result_dict = parsed.model_dump()
            result_dict["estimated_cost_usd"] = est_cost_usd

            record = AiAnalysis(
                domain=domain.lower().strip(),
                analysis_type=analysis_type,
                model_used=model_used,
                structured_output=result_dict,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            return {
                "id": record.id,
                "domain": record.domain,
                "analysis_type": record.analysis_type,
                "model_used": model_used,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "estimated_cost_usd": est_cost_usd,
                "assessment": result_dict,
                "disclaimer": record.disclaimer,
            }
        except (ValidationError, json.JSONDecodeError) as exc:
            last_err = f"Invalid structured JSON from DeepSeek API: {exc}"
        except httpx.HTTPError as exc:
            last_err = f"DeepSeek API request failed: {exc}"
            await asyncio.sleep(1.5 * (attempt + 1))

    return {"status": "error", "error": last_err}