from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models, auth
from app.database import get_db

router = APIRouter(prefix="/executions", tags=["executions"])

@router.get("/", response_model=List[schemas.ExecutionLogBase])
def get_executions(project_id: int = Query(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        logs = db.query(models.ExecutionLog).filter(
            models.ExecutionLog.user_id == current_user.id,
            models.ExecutionLog.project_id == project_id
        ).order_by(models.ExecutionLog.id.desc()).limit(50).all()
        return logs[::-1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/steps/{step_id}/execute")
def mark_step_complete(step_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        step = db.query(models.PlanStep).join(models.Plan).filter(
            models.PlanStep.id == step_id,
            models.Plan.user_id == current_user.id
        ).first()
        
        if not step:
            raise HTTPException(status_code=404, detail="Step not found or access denied")
        
        step.is_completed = True
        log_msg = models.ExecutionLog(
            user_id=current_user.id, 
            project_id=step.plan.project_id, 
            step_id=step.id, 
            level="success", 
            message=f"Step {step.order_index} completed: {step.title}"
        )
        db.add(log_msg)
        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
