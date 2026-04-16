from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db
from schema.models import CaseIn, CaseOut, CaseUpdate
from cases import case_manager as cm

router = APIRouter(prefix="/api/cases", tags=["cases"])

@router.get("", response_model=List[CaseOut])
def list_cases(db: Session=Depends(get_db)):
    cases = cm.list_all(db)
    out = []
    for c in cases:
        d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        d["alert_count"] = cm.get_alert_count(db, c.id)
        out.append(d)
    return out

@router.post("", response_model=CaseOut)
def create_case(body: CaseIn, db: Session=Depends(get_db)):
    c = cm.create(db, body.title, body.description, body.priority,
                  body.assigned_to, body.tags, body.alert_ids)
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["alert_count"] = 0
    return d

@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session=Depends(get_db)):
    c = cm.get(db, case_id)
    if not c: raise HTTPException(404,"Case not found")
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["alert_count"] = cm.get_alert_count(db, case_id)
    return d

@router.put("/{case_id}", response_model=CaseOut)
def update_case(case_id: str, body: CaseUpdate, db: Session=Depends(get_db)):
    c = cm.update(db, case_id, **body.model_dump(exclude_none=True))
    if not c: raise HTTPException(404,"Case not found")
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["alert_count"] = cm.get_alert_count(db, case_id)
    return d

@router.delete("/{case_id}")
def delete_case(case_id: str, db: Session=Depends(get_db)):
    if not cm.delete(db, case_id): raise HTTPException(404,"Case not found")
    return {"deleted": case_id}

@router.post("/{case_id}/alerts/{alert_id}")
def link_alert(case_id: str, alert_id: str, db: Session=Depends(get_db)):
    ok = cm.link_alert(db, case_id, alert_id)
    return {"linked": ok}
