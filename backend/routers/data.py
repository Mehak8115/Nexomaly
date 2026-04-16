import os, shutil
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db
from db.models import UploadedDataset
from pipeline.ingestion import ingest_csv, activate_dataset
from training.trainer import train_all
from config import settings

router = APIRouter(prefix="/api/data", tags=["data"])

@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    auto_train: bool = True,
    db: Session = Depends(get_db),
    background: BackgroundTasks = BackgroundTasks(),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")

    # Save raw upload
    raw_path = os.path.join(settings.DATA_PATH, "uploads", file.filename)
    with open(raw_path, "wb") as f:
        content = await file.read()
        f.write(content)

    ok, meta = ingest_csv(raw_path, file.filename, db)
    if not ok:
        raise HTTPException(422, meta.get("error","Ingestion failed"))

    if auto_train:
        background.add_task(
            train_all, db,
            model_types=["isolation_forest","random_forest"],
            use_feedback=False,
            dataset_id=meta["dataset_id"]
        )

    return {**meta, "auto_train": auto_train,
            "message": "Dataset uploaded. Training started in background." if auto_train
                       else "Dataset uploaded successfully."}

@router.get("/datasets")
def list_datasets(db: Session=Depends(get_db)):
    return db.query(UploadedDataset).order_by(UploadedDataset.created_at.desc()).all()

@router.post("/datasets/{dataset_id}/activate")
def activate(dataset_id: int, db: Session=Depends(get_db)):
    ok = activate_dataset(dataset_id, db)
    if not ok: raise HTTPException(404,"Dataset not found")
    return {"activated": dataset_id}

@router.post("/train")
def manual_train(
    background: BackgroundTasks,
    model_types: str = "isolation_forest,random_forest",
    use_feedback: bool = True,
    db: Session = Depends(get_db),
):
    types = [t.strip() for t in model_types.split(",")]
    background.add_task(train_all, db, model_types=types, use_feedback=use_feedback)
    return {"status":"training_started","models": types}
