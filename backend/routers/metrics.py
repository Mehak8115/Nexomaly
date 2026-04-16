from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db
from monitoring.metrics_tracker import (get_dashboard_stats, get_hourly_trend,
    get_distribution, get_performance_summary, get_latest_model_metrics)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/dashboard")
def dashboard(db: Session=Depends(get_db)):
    return get_dashboard_stats(db)

@router.get("/hourly")
def hourly(hours: int=24, db: Session=Depends(get_db)):
    return get_hourly_trend(db, hours)

@router.get("/distribution")
def distribution(db: Session=Depends(get_db)):
    return get_distribution(db)

@router.get("/performance")
def performance(db: Session=Depends(get_db)):
    return get_performance_summary(db)

@router.get("/models")
def model_metrics(db: Session=Depends(get_db)):
    return get_latest_model_metrics(db)
