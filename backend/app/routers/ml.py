from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ml.engine import train_spam_classifier_from_human_labels
from app.models.models import Backlink, MlTrainingLabel
from app.schemas import TrainingLabelRequest

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post("/train-spam")
def train_ml_spam(db: Session = Depends(get_db)):
    return train_spam_classifier_from_human_labels(db)


@router.post("/labels", status_code=201)
def add_training_label(payload: TrainingLabelRequest, db: Session = Depends(get_db)):
    bl = db.query(Backlink).filter(Backlink.id == payload.backlink_id).first()
    if not bl:
        raise HTTPException(status_code=404, detail="Backlink not found.")
    existing = db.query(MlTrainingLabel).filter(MlTrainingLabel.backlink_id == payload.backlink_id).first()
    if existing:
        existing.is_spam = payload.is_spam
        existing.reviewer_note = payload.reviewer_note
        db.commit()
        return {"id": existing.id, "backlink_id": existing.backlink_id, "is_spam": existing.is_spam, "updated": True}
    label = MlTrainingLabel(
        backlink_id=payload.backlink_id,
        is_spam=payload.is_spam,
        reviewer_note=payload.reviewer_note,
    )
    db.add(label)
    db.commit()
    db.refresh(label)
    return {"id": label.id, "backlink_id": label.backlink_id, "is_spam": label.is_spam, "updated": False}


@router.get("/labels")
def list_training_labels(
    domain: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(MlTrainingLabel, Backlink).join(Backlink, MlTrainingLabel.backlink_id == Backlink.id)
    if domain:
        q = q.filter(Backlink.target_domain == domain.removeprefix("www.").lower().strip())
    total = q.count()
    rows = q.order_by(desc(MlTrainingLabel.labeled_at)).offset((page - 1) * page_size).limit(page_size).all()
    label_count = db.query(func.count(MlTrainingLabel.id)).scalar() or 0
    spam_count = db.query(func.count(MlTrainingLabel.id)).filter(MlTrainingLabel.is_spam.is_(True)).scalar() or 0
    return {
        "total": total,
        "total_labels": label_count,
        "spam_labels": spam_count,
        "not_spam_labels": label_count - spam_count,
        "items": [
            {
                "label_id": lbl.id,
                "backlink_id": lbl.backlink_id,
                "is_spam": lbl.is_spam,
                "reviewer_note": lbl.reviewer_note,
                "labeled_at": lbl.labeled_at,
                "source_domain": bl.source_domain,
                "anchor_text": bl.anchor_text,
                "source_url": bl.source_url,
                "target_domain": bl.target_domain,
            }
            for lbl, bl in rows
        ],
    }


@router.delete("/labels/{label_id}", status_code=204)
def delete_training_label(label_id: int, db: Session = Depends(get_db)):
    lbl = db.query(MlTrainingLabel).filter(MlTrainingLabel.id == label_id).first()
    if not lbl:
        raise HTTPException(status_code=404, detail="Label not found.")
    db.delete(lbl)
    db.commit()
