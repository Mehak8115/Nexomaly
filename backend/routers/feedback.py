from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db
from schema.models import FeedbackIn, FeedbackOut
from feedback import fp_manager as fpm

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

@router.get("", response_model=List[FeedbackOut])
def list_feedback(db: Session=Depends(get_db)):
    return fpm.list_all(db)

@router.get("/stats")
def feedback_stats(db: Session=Depends(get_db)):
    return fpm.stats(db)

@router.post("", response_model=FeedbackOut)
def submit_feedback(body: FeedbackIn, db: Session=Depends(get_db)):
    return fpm.submit(db, body.alert_id, body.transaction_id,
                      body.analyst, body.label, body.reason, body.confidence)

@router.post("/retrain")
def retrain(background: BackgroundTasks, db: Session=Depends(get_db)):
    from training.trainer import train_all
    background.add_task(train_all, db, use_feedback=True)
    return {"status":"training_started","message":"Retraining in background with feedback data"}
