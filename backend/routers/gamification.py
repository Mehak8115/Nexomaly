"""Gamification API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db
from gamification.engine import (get_full_profile, award_xp, get_or_create_daily_challenges,
                                  update_challenge_progress, BADGES, XP)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


@router.get("/profile/{analyst_name}")
def profile(analyst_name: str, db: Session = Depends(get_db)):
    return get_full_profile(db, analyst_name)


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    from db.gamification_models import LeaderboardEntry
    entries = db.query(LeaderboardEntry).order_by(LeaderboardEntry.xp.desc()).limit(10).all()
    return [{"rank": i+1, "name": e.analyst_name, "display": e.display_name,
             "xp": e.xp, "level": e.level, "detection_rate": e.detection_rate,
             "fp_rate": e.fp_rate, "cases_closed": e.cases_closed,
             "fraud_prevented": e.fraud_prevented} for i, e in enumerate(entries)]


@router.get("/challenges")
def challenges(db: Session = Depends(get_db)):
    return get_or_create_daily_challenges(db)


@router.post("/award")
def award(analyst_name: str, event_type: str, description: str = "",
          amount: float = 0, db: Session = Depends(get_db)):
    metadata = {"amount": amount} if amount else {}
    result = award_xp(db, analyst_name, event_type, description, metadata)
    update_challenge_progress(db, event_type, metadata)
    return result


@router.get("/badges")
def badges():
    return [{"key": k, "icon": v[0], "name": v[1],
             "description": v[2], "xp": v[3]} for k, v in BADGES.items()]


@router.get("/xp-table")
def xp_table():
    return XP
