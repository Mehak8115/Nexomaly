"""Unified risk scoring entry point."""
from typing import Dict, Any
from models.ensemble import compute
from explainability.shap_explainer import explain, top_reasons
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


def score_transaction(features: Dict[str, float], tx: Dict[str, Any]) -> Dict[str, Any]:
    ensemble, if_score, rf_score, stat_score, behav_score, ml_score = compute(features)
    level   = _level(ensemble)
    reason  = top_reasons(features, ensemble)
    contribs = explain(features, ensemble)
    return {
        "risk_score":            ensemble,
        "isolation_score":       if_score,
        "rf_score":              rf_score,
        "statistical_score":     stat_score,
        "behavioral_score":      behav_score,
        "ml_score":              ml_score,
        "level":                 level,
        "reason":                reason,
        "feature_contributions": contribs,
        "raw_features":          {k: round(v, 4) for k, v in features.items()},
    }


def _level(score: float) -> str:
    if score >= settings.RISK_THRESHOLD_HIGH:   return "high"
    if score >= settings.RISK_THRESHOLD_MEDIUM: return "medium"
    return "low"
