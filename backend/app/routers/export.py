import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Backlink

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/backlinks")
def export_backlinks_csv(domain: str = Query(...), db: Session = Depends(get_db)):
    clean = domain.removeprefix("www.").lower().strip()
    rows = db.query(Backlink).filter(Backlink.target_domain == clean).order_by(desc(Backlink.last_verified_at)).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Source Domain", "Source URL", "Target URL", "Anchor Text", "DoFollow", "NoFollow", "Sponsored", "UGC", "Status", "Last Verified"])
    for b in rows:
        writer.writerow([
            b.id, b.source_domain, b.source_url, b.target_url, b.anchor_text,
            b.is_dofollow, b.is_nofollow, b.is_sponsored, b.is_ugc, b.status, b.last_verified_at,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{clean}_backlinks.csv"'},
    )
