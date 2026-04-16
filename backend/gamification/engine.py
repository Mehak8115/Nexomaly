"""
Gamification engine.
Handles XP awards, achievement unlocks, daily challenges, leaderboard.
"""
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from db.gamification_models import (AnalystProfile, Achievement,
                                     XPEvent, DailyChallenge, LeaderboardEntry)

# ── XP values ─────────────────────────────────────────────────────────────────
XP = {
    "confirmed_fraud":    100,
    "case_completed":      50,
    "new_pattern":        200,
    "model_improvement":   25,
    "false_positive":     -50,
    "speed_bonus_60s":     75,
    "speed_bonus_300s":    40,
    "accuracy_bonus":      30,
    "consistency_bonus":   50,
    "innovation":         150,
}

# ── Level thresholds ───────────────────────────────────────────────────────────
LEVELS = [
    (0,    1, "Rookie Analyst"),
    (500,  2, "Junior Investigator"),
    (1500, 3, "Fraud Analyst"),
    (3000, 4, "Senior Analyst"),
    (6000, 5, "Lead Investigator"),
    (10000,6, "Fraud Specialist"),
    (15000,7, "Principal Analyst"),
    (25000,8, "Fraud Architect"),
    (40000,9, "Elite Detector"),
    (60000,10,"Guardian of Finance"),
]

# ── Badge definitions ──────────────────────────────────────────────────────────
BADGES = {
    "first_blood":    ("🩸", "First Blood",       "First confirmed fraud detection",              100),
    "eagle_eye":      ("🦅", "Eagle Eye",          "Detect complex multi-step fraud",              300),
    "speed_demon":    ("⚡", "Speed Demon",         "Catch fraud within 1 minute",                  200),
    "pattern_master": ("🔍", "Pattern Master",      "Identify 5 new fraud patterns",               500),
    "clean_sweep":    ("✨", "Clean Sweep",          "Full week with zero false positives",          400),
    "guardian":       ("🛡️","Guardian",             "Prevent $1M+ in fraud losses",                1000),
    "detective":      ("🕵️","Detective",            "Investigate and close 100 cases",              750),
    "innovator":      ("💡", "Innovator",           "Trigger model retrain improving accuracy",     600),
    "centurion":      ("💯", "Centurion",           "Confirm 100 true positive detections",         500),
    "precision":      ("🎯", "Precision",           "10 consecutive detections with no FP",         350),
    "night_owl":      ("🦉", "Night Owl",           "Detect 10 fraud cases during night hours",     200),
    "marathon":       ("🏃", "Marathon",            "Active for 30 consecutive days",               800),
    "top_gun":        ("🏆", "Top Gun",             "Reach #1 on leaderboard",                      500),
    "million_dollar": ("💰", "Million Dollar",      "Single detection preventing $100K+ fraud",     400),
    "false_alarm":    ("🚨", "Calibrated",          "Reduce FP rate below 2%",                      300),
}

# ── Daily challenge templates ──────────────────────────────────────────────────
CHALLENGE_TEMPLATES = [
    ("rush_hour",       "Rush Hour",        "⚡", "Confirm 5 alerts during peak hours (9AM-5PM)", 5,  150),
    ("pattern_hunt",    "Pattern Hunt",     "🔍", "Identify 3 high-risk merchant patterns",       3,  200),
    ("optimization",    "Optimization Day", "⚙️", "Submit feedback on 3 false positives",         3,  175),
    ("speed_trial",     "Speed Trial",      "🏎️", "Confirm 3 alerts within 2 minutes each",       3,  225),
    ("threshold_tune",  "Threshold Tuning", "🎛️", "Trigger a model retrain",                      1,  300),
    ("feature_hunt",    "Feature Discovery","🧬", "Review 10 different alert types",              10, 150),
    ("model_marathon",  "Model Marathon",   "🤖", "Confirm 10 alerts of any type",                10, 250),
]


def get_or_create_profile(db: Session, analyst_name: str) -> AnalystProfile:
    p = db.query(AnalystProfile).filter(AnalystProfile.analyst_name == analyst_name).first()
    if not p:
        p = AnalystProfile(analyst_name=analyst_name, display_name=analyst_name,
                           xp=0, level=1, title="Rookie Analyst",
                           created_at=datetime.utcnow())
        db.add(p); db.commit(); db.refresh(p)
    return p


def award_xp(db: Session, analyst_name: str, event_type: str,
             description: str, metadata: Dict = None) -> Dict[str, Any]:
    """Award or deduct XP and check for level-up + achievements."""
    delta = XP.get(event_type, 0)
    if delta == 0:
        return {"xp_delta": 0}

    profile = get_or_create_profile(db, analyst_name)
    old_level = profile.level

    # Log XP event
    ev = XPEvent(analyst_name=analyst_name, event_type=event_type,
                 xp_delta=delta, description=description,
                 metadata_json=metadata or {}, created_at=datetime.utcnow())
    db.add(ev)

    # Update XP (floor at 0)
    profile.xp = max(0, profile.xp + delta)
    profile.last_active = datetime.utcnow()

    # Update stats
    if event_type == "confirmed_fraud":
        profile.total_detections += 1
        if metadata and metadata.get("amount"):
            profile.fraud_prevented += float(metadata["amount"])
    elif event_type == "false_positive":
        profile.total_fp += 1
    elif event_type == "case_completed":
        profile.total_cases += 1

    # Level up
    new_level, new_title = _compute_level(profile.xp)
    level_up = new_level > old_level
    profile.level = new_level
    profile.title = new_title

    db.commit()

    # Check achievements
    unlocked = _check_achievements(db, profile)

    # Update leaderboard
    _update_leaderboard(db, profile)

    return {
        "xp_delta":  delta,
        "new_xp":    profile.xp,
        "new_level": profile.level,
        "level_up":  level_up,
        "title":     profile.title,
        "achievements_unlocked": unlocked,
    }


def _compute_level(xp: int):
    level, title = 1, "Rookie Analyst"
    for threshold, lvl, t in LEVELS:
        if xp >= threshold:
            level, title = lvl, t
    return level, title


def _check_achievements(db: Session, profile: AnalystProfile) -> List[Dict]:
    unlocked = []
    existing = {a.badge_key for a in db.query(Achievement)
                .filter(Achievement.analyst_name == profile.analyst_name).all()}

    def _unlock(key):
        if key in existing or key not in BADGES:
            return
        icon, name, desc, xp_award = BADGES[key]
        ach = Achievement(analyst_name=profile.analyst_name, badge_key=key,
                          badge_name=name, description=desc, icon=icon,
                          xp_awarded=xp_award, unlocked_at=datetime.utcnow())
        db.add(ach)
        profile.xp += xp_award
        unlocked.append({"key": key, "name": name, "icon": icon, "xp": xp_award})

    if profile.total_detections >= 1:   _unlock("first_blood")
    if profile.total_detections >= 100: _unlock("centurion")
    if profile.total_cases >= 100:      _unlock("detective")
    if profile.fraud_prevented >= 1_000_000: _unlock("guardian")
    if profile.fraud_prevented >= 100_000:   _unlock("million_dollar")
    if profile.level >= 1 and profile.total_fp == 0 and profile.total_detections >= 10:
        _unlock("precision")

    # Check FP rate
    total = profile.total_detections + profile.total_fp
    if total > 20:
        fp_rate = profile.total_fp / total
        if fp_rate < 0.02: _unlock("false_alarm")

    if unlocked:
        db.commit()
    return unlocked


def get_or_create_daily_challenges(db: Session) -> List[DailyChallenge]:
    """Get today's challenges, creating them if they don't exist."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    existing = db.query(DailyChallenge).filter(
        DailyChallenge.expires_at > datetime.utcnow(),
        DailyChallenge.expires_at <= tomorrow + timedelta(days=1)
    ).all()

    if len(existing) >= 3:
        return existing

    # Delete old
    db.query(DailyChallenge).filter(DailyChallenge.expires_at <= datetime.utcnow()).delete()

    # Create 3 random challenges for today
    import random
    selected = random.sample(CHALLENGE_TEMPLATES, min(3, len(CHALLENGE_TEMPLATES)))
    challenges = []
    for key, title, icon, desc, target, xp_reward in selected:
        c = DailyChallenge(challenge_key=key, title=title, description=desc,
                           icon=icon, target_value=target, current_value=0,
                           xp_reward=xp_reward, completed=False,
                           expires_at=tomorrow, created_at=datetime.utcnow())
        db.add(c); challenges.append(c)
    db.commit()

    for c in challenges:
        db.refresh(c)
    return challenges


def update_challenge_progress(db: Session, event_type: str, metadata: Dict = None):
    """Increment challenge progress based on action."""
    challenges = db.query(DailyChallenge).filter(
        DailyChallenge.expires_at > datetime.utcnow(),
        DailyChallenge.completed == False
    ).all()

    mapping = {
        "confirmed_fraud":  ["rush_hour","pattern_hunt","speed_trial","model_marathon"],
        "false_positive":   ["optimization"],
        "case_completed":   ["feature_hunt","model_marathon"],
        "model_improvement":["threshold_tune"],
    }

    keys_to_update = mapping.get(event_type, [])
    for c in challenges:
        if c.challenge_key in keys_to_update:
            c.current_value = min(c.current_value + 1, c.target_value)
            if c.current_value >= c.target_value:
                c.completed = True
    db.commit()


def _update_leaderboard(db: Session, profile: AnalystProfile):
    total = profile.total_detections + profile.total_fp
    fp_rate = round(profile.total_fp / total * 100, 1) if total > 0 else 0.0
    dr      = round(profile.total_detections / max(total, 1) * 100, 1)

    entry = db.query(LeaderboardEntry).filter(
        LeaderboardEntry.analyst_name == profile.analyst_name).first()
    if not entry:
        entry = LeaderboardEntry(analyst_name=profile.analyst_name,
                                 display_name=profile.display_name or profile.analyst_name)
        db.add(entry)

    entry.xp             = profile.xp
    entry.level          = profile.level
    entry.detection_rate = dr
    entry.fp_rate        = fp_rate
    entry.cases_closed   = profile.total_cases
    entry.fraud_prevented= profile.fraud_prevented
    entry.response_time  = profile.avg_response_sec
    entry.updated_at     = datetime.utcnow()
    db.commit()


def get_full_profile(db: Session, analyst_name: str) -> Dict[str, Any]:
    profile     = get_or_create_profile(db, analyst_name)
    achievements= db.query(Achievement).filter(
        Achievement.analyst_name == analyst_name
    ).order_by(Achievement.unlocked_at.desc()).all()
    xp_log      = db.query(XPEvent).filter(
        XPEvent.analyst_name == analyst_name
    ).order_by(XPEvent.created_at.desc()).limit(20).all()
    challenges  = get_or_create_daily_challenges(db)
    leaderboard = db.query(LeaderboardEntry).order_by(
        LeaderboardEntry.xp.desc()).limit(10).all()

    # XP to next level
    next_thresh = None
    for threshold, lvl, _ in LEVELS:
        if lvl == profile.level + 1:
            next_thresh = threshold; break
    xp_progress = 0
    if next_thresh:
        curr_thresh = next((t for t, l, _ in LEVELS if l == profile.level), 0)
        xp_progress = int((profile.xp - curr_thresh) / max(next_thresh - curr_thresh, 1) * 100)

    # All badges (locked + unlocked)
    unlocked_keys = {a.badge_key for a in achievements}
    all_badges = []
    for key, (icon, name, desc, xp_award) in BADGES.items():
        unlocked_ach = next((a for a in achievements if a.badge_key == key), None)
        all_badges.append({
            "key": key, "icon": icon, "name": name, "description": desc,
            "xp": xp_award, "unlocked": key in unlocked_keys,
            "unlocked_at": unlocked_ach.unlocked_at.isoformat() if unlocked_ach else None,
        })

    return {
        "profile": {
            "analyst_name":    profile.analyst_name,
            "display_name":    profile.display_name or profile.analyst_name,
            "xp":              profile.xp,
            "level":           profile.level,
            "title":           profile.title,
            "xp_progress_pct": xp_progress,
            "next_level_xp":   next_thresh,
            "total_detections":profile.total_detections,
            "total_fp":        profile.total_fp,
            "total_cases":     profile.total_cases,
            "fraud_prevented": profile.fraud_prevented,
            "streak_days":     profile.streak_days,
            "created_at":      profile.created_at.isoformat(),
        },
        "badges":      all_badges,
        "xp_log":      [{"type":e.event_type,"delta":e.xp_delta,"desc":e.description,
                          "at":e.created_at.isoformat()} for e in xp_log],
        "challenges":  [{"id":c.id,"key":c.challenge_key,"title":c.title,
                          "desc":c.description,"icon":c.icon,
                          "current":c.current_value,"target":c.target_value,
                          "xp":c.xp_reward,"completed":c.completed,
                          "expires":c.expires_at.isoformat()} for c in challenges],
        "leaderboard": [{"rank":i+1,"name":e.analyst_name,"display":e.display_name,
                          "xp":e.xp,"level":e.level,"dr":e.detection_rate,
                          "fpr":e.fp_rate,"cases":e.cases_closed,
                          "prevented":e.fraud_prevented} for i,e in enumerate(leaderboard)],
    }


def seed_demo_gamification(db: Session):
    """Seed demo analyst profiles and achievements."""
    if db.query(AnalystProfile).count() > 0:
        return

    now = datetime.utcnow()
    analysts = [
        ("Sr. Analyst",  "Sr. Analyst",    8750, 4, "Senior Analyst",       42, 3, 18, 892400.0),
        ("J. Rodriguez", "J. Rodriguez",  12300, 5, "Lead Investigator",    67, 1, 31, 1450000.0),
        ("K. Patel",     "K. Patel",       5200, 3, "Fraud Analyst",        28, 5, 12, 340000.0),
        ("M. Chen",      "M. Chen",       18900, 6, "Fraud Specialist",     95, 0, 52, 2100000.0),
        ("A. Thompson",  "A. Thompson",    3100, 2, "Junior Investigator",  15, 8,  6, 125000.0),
    ]

    for uname, dname, xp, lvl, title, dets, fps, cases, prevented in analysts:
        p = AnalystProfile(analyst_name=uname, display_name=dname, xp=xp, level=lvl,
                           title=title, total_detections=dets, total_fp=fps,
                           total_cases=cases, fraud_prevented=prevented,
                           streak_days=7, last_active=now, created_at=now - timedelta(days=30))
        db.add(p); db.flush()

        # Give them some achievements
        badge_keys = ["first_blood","centurion"] if dets >= 100 else ["first_blood"]
        if prevented >= 1_000_000: badge_keys.append("guardian")
        if cases >= 10: badge_keys.append("detective" if cases >= 100 else "eagle_eye")
        if fps == 0 and dets >= 10: badge_keys.append("precision")

        for key in badge_keys:
            if key in BADGES:
                icon, name, desc, xp_award = BADGES[key]
                db.add(Achievement(analyst_name=uname, badge_key=key, badge_name=name,
                                   description=desc, icon=icon, xp_awarded=xp_award,
                                   unlocked_at=now - timedelta(days=10)))

        # Leaderboard entry
        total = dets + fps
        db.add(LeaderboardEntry(
            analyst_name=uname, display_name=dname, xp=xp, level=lvl,
            detection_rate=round(dets/max(total,1)*100,1),
            fp_rate=round(fps/max(total,1)*100,1),
            cases_closed=cases, fraud_prevented=prevented, updated_at=now))

    db.commit()
    print("[Seed] Gamification demo data inserted ✓")
