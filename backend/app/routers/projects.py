from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Project
from app.schemas import ProjectCreateRequest

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(desc(Project.created_at)).all()
    return {"projects": [{"id": p.id, "name": p.name, "root_domain": p.root_domain, "description": p.description} for p in rows]}


@router.post("")
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db)):
    p = Project(name=payload.name, root_domain=payload.root_domain.lower().strip(), description=payload.description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "root_domain": p.root_domain}
