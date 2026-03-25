from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import schemas, models, auth
from app.database import get_db

router = APIRouter(prefix="/usage", tags=["usage"])

@router.get("/", response_model=schemas.TokenUsageBase)
def get_usage(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        # We need to explicitly handle string conversion for cost or map it as numeric. 
        # Since we stored cost as a string for simplicity, we can fetch all and sum manually if scalar SUM fails on strings in sqlite.
        usages = db.query(models.TokenUsage).filter(models.TokenUsage.user_id == current_user.id).all()
        total_tokens = sum(u.tokens_used for u in usages)
        total_cost = sum(float(u.cost) for u in usages)
        
        return schemas.TokenUsageBase(user_id=current_user.id, tokens_used=total_tokens, cost=f"${total_cost:.4f}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
