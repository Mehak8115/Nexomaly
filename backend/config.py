import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    APP_NAME: str = "AnomalyOS"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/anomalyos.db"
    ML_MODELS_PATH: str = str(BASE_DIR / "models" / "saved")
    UPLOADS_PATH: str = str(BASE_DIR / "uploads")
    DATA_PATH: str = str(ROOT_DIR / "data")
    RISK_THRESHOLD_HIGH: float = 70.0
    RISK_THRESHOLD_MEDIUM: float = 40.0
    SIMULATION_INTERVAL: float = 15.0
    SIMULATION_ENABLED: bool = True
    CORS_ORIGINS: str = "*"
    DEFAULT_ANALYST: str = "Sr. Analyst"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()

# Ensure directories exist
for path in [settings.ML_MODELS_PATH, settings.UPLOADS_PATH,
             settings.DATA_PATH + "/raw", settings.DATA_PATH + "/processed",
             settings.DATA_PATH + "/uploads"]:
    os.makedirs(path, exist_ok=True)
