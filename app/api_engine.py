from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.continuity_service import ContinuityService
from app.services.proactive_service import ProactiveService
from app.services.temporal_service import TemporalService
from app.services.consolidation_service import ConsolidationService

router = APIRouter(prefix="/ai", tags=["ai-engine"])

continuity = ContinuityService()
proactive = ProactiveService()
temporal = TemporalService()
consolidation = ConsolidationService()


@router.get("/projects")
def list_projects(status: Optional[str] = None):
    return {"projects": continuity.list_projects(status=status)}


@router.post("/projects")
def create_project(title: str, description: str = "", priority: str = "medium"):
    pid = continuity.create_project(title, description, priority=priority)
    return continuity.get_project_by_id(pid)


@router.get("/projects/{project_id}")
def get_project(project_id: int):
    p = continuity.get_project_by_id(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/goals")
def list_goals(status: Optional[str] = "active", project_id: Optional[int] = None):
    return {"goals": continuity.list_goals(status=status, project_id=project_id)}


@router.post("/goals")
def create_goal(goal_text: str, project_id: Optional[int] = None, priority: str = "medium"):
    gid = continuity.create_goal(goal_text, project_id=project_id, priority=priority)
    return continuity.get_goal_by_id(gid)


@router.get("/open-loops")
def list_open_loops(status: Optional[str] = "open", project_id: Optional[int] = None):
    return {"open_loops": continuity.list_open_loops(status=status, project_id=project_id)}


@router.post("/open-loops")
def create_open_loop(description: str, project_id: Optional[int] = None, priority: str = "medium"):
    lid = continuity.create_open_loop(description, project_id=project_id, priority=priority)
    return continuity.get_open_loop_by_id(lid)


@router.get("/continuity/snapshot")
def get_continuity_snapshot():
    return continuity.get_continuity_snapshot()


@router.get("/continuity/next-actions")
def get_next_actions(limit: int = Query(8, le=20)):
    return {"actions": continuity.suggest_next_actions(limit=limit)}


@router.get("/proactive/briefing")
def get_proactive_briefing():
    return proactive.generate_proactive_briefing()


@router.get("/temporal/health")
def get_temporal_health():
    return temporal.get_temporal_health_report()


@router.get("/temporal/changes")
def get_temporal_changes():
    return temporal.detect_all_changes()


@router.get("/temporal/reconfirmation")
def get_reconfirmation_candidates(stale_after_days: int = 30):
    return {"candidates": temporal.get_reconfirmation_candidates(stale_after_days)}


@router.get("/stats")
def get_full_stats():
    mem_stats = consolidation.get_memory_stats()
    continuity_snapshot = continuity.get_continuity_snapshot()
    temporal_health = temporal.get_temporal_health_report()
    return {
        "memory": mem_stats,
        "continuity": continuity_snapshot["counts"],
        "temporal": temporal_health["counts"],
    }
