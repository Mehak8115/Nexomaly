from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


# ── Alert ──────────────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: str
    transaction_id: Optional[str] = None
    user_id: str
    amount: float
    risk_score: float
    ml_score: float
    statistical_score: float
    behavioral_score: float
    level: str
    status: str
    reason: str
    explanation_json: Optional[Any] = None
    features_json: Optional[Any] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: str


# ── Case ───────────────────────────────────────────────────────────────────────
class CaseIn(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    assigned_to: str = "Sr. Analyst"
    tags: Optional[List[str]] = []
    alert_ids: Optional[List[str]] = []


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


class CaseNoteIn(BaseModel):
    content: str
    author: str = "Sr. Analyst"


class CaseOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assigned_to: str
    tags: Optional[List] = []
    created_at: datetime
    updated_at: datetime
    alert_count: int = 0
    note_count: int = 0

    class Config:
        from_attributes = True


# ── Feedback ───────────────────────────────────────────────────────────────────
class FeedbackIn(BaseModel):
    alert_id: str
    transaction_id: str
    analyst: str = "Sr. Analyst"
    label: str  # true_positive / false_positive
    reason: str
    confidence: float = 1.0


class FeedbackOut(BaseModel):
    id: int
    alert_id: str
    transaction_id: str
    analyst: str
    label: str
    reason: str
    retrain_used: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Stats ──────────────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_alerts_today: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    open_cases: int
    fp_rate_7d: float
    detection_rate: float
    avg_risk_score: float
    ml_score_avg: float
    statistical_score_avg: float
    behavioral_score_avg: float
    total_alerts_7d: int
    total_feedback: int


class MetricsOut(BaseModel):
    precision: float
    recall: float
    f1_score: float
    fp_rate: float
    detection_rate: float
    roc_auc: Optional[float] = None
    model_version: int = 1
    train_rows: int = 0
    last_trained: Optional[str] = None


class HourlyPoint(BaseModel):
    hour: str
    count: int
    high: int
    medium: int
    low: int


class DistributionOut(BaseModel):
    high: int
    medium: int
    low: int


# ── Dataset Upload ─────────────────────────────────────────────────────────────
class DatasetUploadOut(BaseModel):
    id: int
    filename: str
    rows: int
    columns_json: Optional[Any] = None
    status: str
    error_msg: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ── Model Version ──────────────────────────────────────────────────────────────
class ModelVersionOut(BaseModel):
    id: int
    name: str
    version: int
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    fp_rate: Optional[float] = None
    train_rows: Optional[int] = None
    fp_feedback: int = 0
    is_active: bool
    trained_at: datetime

    class Config:
        from_attributes = True
