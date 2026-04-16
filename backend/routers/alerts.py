from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db
from db.models import Alert
from schema.models import AlertOut, AlertStatusUpdate
from alerts.alert_engine import process
from streaming.simulator import generate_transaction

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[AlertOut])
def list_alerts(level: Optional[str]=None, status: Optional[str]=None,
                search: Optional[str]=None, limit: int=Query(100,le=500),
                db: Session=Depends(get_db)):
    q = db.query(Alert)
    if level  and level  != "all": q = q.filter(Alert.level==level)
    if status and status != "all": q = q.filter(Alert.status==status)
    if search: q = q.filter(Alert.id.contains(search)|Alert.user_id.contains(search))
    return q.order_by(Alert.created_at.desc()).limit(limit).all()

@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: str, db: Session=Depends(get_db)):
    a = db.query(Alert).filter(Alert.id==alert_id).first()
    if not a: raise HTTPException(404,"Alert not found")
    return a

@router.put("/{alert_id}/status")
def update_status(alert_id: str, body: AlertStatusUpdate, db: Session=Depends(get_db)):
    a = db.query(Alert).filter(Alert.id==alert_id).first()
    if not a: raise HTTPException(404,"Alert not found")
    a.status = body.status; db.commit()
    return {"id": alert_id, "status": body.status}

@router.post("/simulate")
async def simulate(db: Session=Depends(get_db)):
    from main import manager
    tx    = generate_transaction()
    alert = process(tx, db, save=True)
    if alert:
        await manager.broadcast({"type":"alert","data":alert})
        return alert
    return {"message":"Transaction below alert threshold"}
