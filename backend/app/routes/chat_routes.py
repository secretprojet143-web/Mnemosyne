from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models, auth
from app.database import get_db
from app.limiter import limiter

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/", response_model=schemas.ChatResponse)
@limiter.limit("20/minute")
def post_chat(
    request: Request,
    prompt: schemas.ChatPrompt, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # Validate project belongs to user
        project = db.query(models.Project).filter(models.Project.id == prompt.project_id, models.Project.user_id == current_user.id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        user_msg = models.Conversation(user_id=current_user.id, project_id=prompt.project_id, sender="user", text=prompt.text)
        db.add(user_msg)
        
        system_response_text = f"Analyzed command '{prompt.text}'. Executing Mnemosyne core routines."
        plan_title = f"Task: {prompt.text[:30]}..."
        
        steps_data = [
            {"o": 1, "t": "Analyze Input", "d": "Parse prompt intent"},
            {"o": 2, "t": "Context Retrieval", "d": "Fetch memory embeddings"},
            {"o": 3, "t": "Execution", "d": "Run core AI models"}
        ]
        
        system_msg = models.Conversation(user_id=current_user.id, project_id=prompt.project_id, sender="system", text=system_response_text)
        db.add(system_msg)
        
        new_plan = models.Plan(user_id=current_user.id, project_id=prompt.project_id, title=plan_title)
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        
        for step_cfg in steps_data:
            step_model = models.PlanStep(
                plan_id=new_plan.id,
                order_index=step_cfg["o"],
                title=step_cfg["t"],
                description=step_cfg["d"]
            )
            db.add(step_model)
        db.commit()
        
        first_step = db.query(models.PlanStep).filter(models.PlanStep.plan_id == new_plan.id).order_by(models.PlanStep.order_index).first()
        if first_step:
            log_msg = models.ExecutionLog(user_id=current_user.id, project_id=prompt.project_id, step_id=first_step.id, level="info", message=f"Mnemosyne plan initiated: {plan_title}")
            db.add(log_msg)
        
        estimated_tokens = len(prompt.text) * 2 + len(system_response_text) * 2
        cost = estimated_tokens * 0.00001
        usage = models.TokenUsage(user_id=current_user.id, tokens_used=estimated_tokens, cost=str(cost))
        db.add(usage)
        
        db.commit()
        return {"status": "ok", "message": system_msg.text}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Mnemosyne Engine Error: {str(e)}")

@router.get("/", response_model=List[schemas.ConversationBase])
def get_chat_history(project_id: int = Query(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    try:
        msgs = db.query(models.Conversation).filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.project_id == project_id
        ).order_by(models.Conversation.id.asc()).all()
        return msgs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
