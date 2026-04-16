"""Dashboard KPIs, trend data, and performance metrics."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Alert, Case, Feedback, ModelMetrics


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    today   = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    since7d = datetime.utcnow() - timedelta(days=7)

    total_today = db.query(Alert).filter(Alert.created_at >= today).count()
    high_today  = db.query(Alert).filter(Alert.created_at >= today, Alert.level=="high").count()
    med_today   = db.query(Alert).filter(Alert.created_at >= today, Alert.level=="medium").count()
    low_today   = db.query(Alert).filter(Alert.created_at >= today, Alert.level=="low").count()
    open_cases  = db.query(Case).filter(Case.status.in_(["open","investigating"])).count()
    total_all   = db.query(Alert).count()
    total_fb    = db.query(Feedback).count()

    total7 = db.query(Alert).filter(Alert.created_at >= since7d).count()
    fp7    = db.query(Alert).filter(Alert.created_at >= since7d,
                                    Alert.status == "false_positive").count()
    fp_rate = round(fp7 / total7 * 100, 1) if total7 > 0 else 0.0

    recent = db.query(Alert).filter(Alert.created_at >= since7d).all()
    def avg(field):
        vals = [getattr(a, field, 0) or 0 for a in recent]
        return round(sum(vals)/len(vals), 1) if vals else 0.0

    return {
        "total_alerts_today":    total_today,
        "high_risk_count":       high_today,
        "medium_risk_count":     med_today,
        "low_risk_count":        low_today,
        "open_cases":            open_cases,
        "fp_rate_7d":            fp_rate,
        "avg_risk_score":        avg("risk_score"),
        "ml_score_avg":          avg("ml_score"),
        "statistical_score_avg": avg("statistical_score"),
        "behavioral_score_avg":  avg("behavioral_score"),
        "total_alerts_all_time": total_all,
        "total_feedback":        total_fb,
    }


def get_hourly_trend(db: Session, hours: int = 24) -> List[Dict]:
    """Returns hourly trend in UTC — frontend converts to local time."""
    now = datetime.utcnow()
    result = []
    for i in range(hours - 1, -1, -1):
        t0 = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
        t1 = t0 + timedelta(hours=1)
        rows = db.query(Alert).filter(Alert.created_at >= t0,
                                       Alert.created_at <  t1).all()
        result.append({
            "hour":   t0.strftime("%H:00"),
            "count":  len(rows),
            "high":   sum(1 for r in rows if r.level == "high"),
            "medium": sum(1 for r in rows if r.level == "medium"),
            "low":    sum(1 for r in rows if r.level == "low"),
        })
    return result


def get_distribution(db: Session, since_hours: int = 24) -> Dict[str, int]:
    since = datetime.utcnow() - timedelta(hours=since_hours)
    rows  = db.query(Alert).filter(Alert.created_at >= since).all()
    return {
        "high":   sum(1 for r in rows if r.level == "high"),
        "medium": sum(1 for r in rows if r.level == "medium"),
        "low":    sum(1 for r in rows if r.level == "low"),
    }


def get_performance_summary(db: Session) -> Dict[str, Any]:
    """
    Live performance calculated PURELY from analyst feedback.
    Model training metrics shown separately in get_latest_model_metrics().
    """
    feedbacks = db.query(Feedback).all()
    total_alerts = db.query(Alert).count()

    if not feedbacks:
        return {
            "precision": 0.0, "recall": 0.0, "f1_score": 0.0,
            "fp_rate": 0.0, "detection_rate": 0.0, "auc_roc": 0.0,
            "total_predictions": total_alerts,
            "true_positives": 0, "false_positives": 0,
            "true_negatives": 0, "false_negatives": 0,
        }

    tp = sum(1 for f in feedbacks if f.label == "true_positive")
    fp = sum(1 for f in feedbacks if f.label == "false_positive")
    total_reviewed = len(feedbacks)

    # Estimate FN: assume 5% of unreviewed alerts are missed fraud
    unreviewed = total_alerts - total_reviewed
    fn = max(0, round(unreviewed * 0.05))
    tn = max(0, total_alerts - tp - fp - fn)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2*precision*recall/(precision+recall) if (precision+recall) > 0 else 0.0
    fp_rate   = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "precision":        round(precision, 4),
        "recall":           round(recall,    4),
        "f1_score":         round(f1,        4),
        "fp_rate":          round(fp_rate,   4),
        "detection_rate":   round(recall,    4),
        "auc_roc":          0.0,
        "total_predictions":total_alerts,
        "true_positives":   tp,
        "false_positives":  fp,
        "true_negatives":   tn,
        "false_negatives":  fn,
    }


def get_latest_model_metrics(db: Session) -> List[Dict]:
    results = []
    for model_name in ("isolation_forest", "random_forest"):
        m = (db.query(ModelMetrics)
               .filter(ModelMetrics.model_name == model_name)
               .order_by(ModelMetrics.created_at.desc())
               .first())
        if m:
            results.append({
                "model_name":    m.model_name,
                "version":       m.version,
                "precision":     m.precision,
                "recall":        m.recall,
                "f1_score":      m.f1_score,
                "fp_rate":       m.fp_rate,
                "detection_rate":m.detection_rate,
                "auc_roc":       m.auc_roc,
                "n_samples":     m.n_samples,
                "trained_on":    m.trained_on,
                "created_at":    m.created_at.isoformat(),
            })
    return results
