from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models, auth
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=List[schemas.ProjectBase])
def get_projects(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        projects = db.query(models.Project).filter(models.Project.user_id == current_user.id).order_by(models.Project.updated_at.desc()).all()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=schemas.ProjectBase)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        new_proj = models.Project(user_id=current_user.id, title=project.title)
        db.add(new_proj)
        db.commit()
        db.refresh(new_proj)
        return new_proj
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
