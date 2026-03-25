from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models, auth
from app.database import get_db

router = APIRouter(prefix="/plans", tags=["plans"])

@router.get("/", response_model=List[schemas.PlanBase])
def get_plans(project_id: int = Query(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        plans = db.query(models.Plan).filter(
            models.Plan.user_id == current_user.id,
            models.Plan.project_id == project_id
        ).order_by(models.Plan.id.desc()).all()
        return plans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
