from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from app.config import settings, DOCS_DIR
from app.db.schema import init_db
from app.services.llm_service import LLMService, OpenRouterError
from app.services.routing_service import RoutingService
from app.services.memory_service import MemoryService
from app.services.prompt_builder import PromptBuilder
from app.services.profile_service import ProfileService
from app.services.rag_service import RAGService
from app.services.semantic_memory_service import SemanticMemoryService
from app.services.evolution_service import EvolutionService
from app.services.consolidation_service import ConsolidationService
from app.services.retrieval_orchestrator import RetrievalOrchestrator
from app.services.continuity_service import ContinuityService
from app.services.continuity_extractor import ContinuityExtractor
from app.services.observability_service import ObservabilityService
from app.services.evaluation_service import EvaluationService
from app.services.job_service import JobService
from app.services.recommendation_service import RecommendationService
from app.services.temporal_service import TemporalService
from app.services.proactive_service import ProactiveService
from app.services.initiative_service import InitiativeService
from app.services.reasoning_service import ReasoningService
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.tool_registry_service import ToolRegistryService
from app.services.tool_execution_service import ToolExecutionService
from app.services.tool_policy_service import ToolPolicyService
from app.services.tool_control_service import ToolControlService
from app.services.trust_service import TrustService
from app.services.prompt_security_service import PromptSecurityService
from app.services.permission_service import PermissionService
from app.services.security_scan_service import SecurityScanService
from app.services.autonomy_service import AutonomyService
from app.auth_api import router as auth_router
from app.api_memory import router as api_memory_router
from app.api_engine import router as api_engine_router

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth endpoints for React frontend
app.include_router(auth_router)
# Memory + facts API
app.include_router(api_memory_router)
# AI engine API (projects, goals, loops, proactive, temporal)
app.include_router(api_engine_router)

# Serve React frontend from frontend/dist/
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"
UI_DIR = Path(__file__).parent.parent / "ui"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="frontend_assets")

if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


@app.get("/")
def serve_root():
    # Serve React frontend if it exists
    if FRONTEND_DIR.exists():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    # Fallback to old UI
    index_file = UI_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Mnemosyne AI is running. Build the frontend or add ui/index.html"}


llm_service = LLMService()
routing_service = RoutingService()
memory_service = MemoryService()
prompt_builder = PromptBuilder()
profile_service = ProfileService()
rag_service = RAGService()
semantic_memory_service = SemanticMemoryService()
evolution_service = EvolutionService()
consolidation_service = ConsolidationService()
retrieval_orchestrator = RetrievalOrchestrator()
continuity_service = ContinuityService()
continuity_extractor = ContinuityExtractor()
observability_service = ObservabilityService()
evaluation_service = EvaluationService()
job_service = JobService()
recommendation_service = RecommendationService()
temporal_service = TemporalService()
proactive_service = ProactiveService()
initiative_service = InitiativeService()
reasoning_service = ReasoningService()
planning_service = PlanningService()
execution_service = ExecutionService()
tool_registry_service = ToolRegistryService()
tool_execution_service = ToolExecutionService()
tool_policy_service = ToolPolicyService()
tool_control_service = ToolControlService()
trust_service = TrustService()
prompt_security_service = PromptSecurityService()
permission_service = PermissionService()
security_scan_service = SecurityScanService()
autonomy_service = AutonomyService()


def safe_background_consolidation(conversation_id: int):
    try:
        result = consolidation_service.check_and_consolidate_conversation(conversation_id)
        observability_service.log_background_consolidation(conversation_id, result)
    except Exception as e:
        observability_service.log_error(
            event_type="background_consolidation_error",
            error=str(e),
            extra={"conversation_id": conversation_id}
        )


VALID_RETRIEVAL_MODES = {
    "balanced",
    "deep_memory",
    "focused",
    "document_first",
    "privacy_safe"
}

VALID_PROJECT_STATUSES = {"active", "paused", "completed", "archived"}
VALID_GOAL_STATUSES = {"active", "completed", "abandoned"}
VALID_OPEN_LOOP_STATUSES = {"open", "resolved", "dropped"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_INITIATIVE_MODES = {"quiet", "balanced", "active", "coach"}
VALID_REASONING_STATUSES = {"draft", "active", "completed", "abandoned"}
VALID_PLAN_STATUSES = {"draft", "active", "completed", "abandoned"}
VALID_PLAN_STEP_STATUSES = {"pending", "in_progress", "completed", "blocked", "failed", "skipped"}
VALID_EXECUTION_STATUSES = {"pending", "running", "succeeded", "failed", "cancelled"}
VALID_VERIFICATION_STATUSES = {"unverified", "verified", "verification_failed"}
VALID_AUTONOMY_RUN_STATUSES = {"draft", "running", "paused", "completed", "stopped", "failed"}


class ChatRequest(BaseModel):
    message: str
    system_prompt: str | None = None
    conversation_id: int | None = None
    retrieval_mode: str | None = "balanced"
    initiative_mode: str | None = "balanced"
    mode: str | None = "standard"


VALID_CHAT_MODES = {"fast", "standard", "deep"}


class ReasoningStateCreateRequest(BaseModel):
    conversation_id: int | None = None
    project_id: int | None = None
    task: str
    goal: str | None = ""
    constraints: list[str] | None = None
    assumptions: list[str] | None = None
    candidate_actions: list[str] | None = None
    selected_action: str | None = None
    confidence: float | None = 0.5
    self_check: dict | None = None
    status: str | None = "draft"


class ReasoningStateUpdateRequest(BaseModel):
    task: str | None = None
    goal: str | None = None
    constraints: list[str] | None = None
    assumptions: list[str] | None = None
    candidate_actions: list[str] | None = None
    selected_action: str | None = None
    confidence: float | None = None
    self_check: dict | None = None
    status: str | None = None


class ReasoningStateGenerateRequest(BaseModel):
    user_input: str
    conversation_id: int | None = None
    project_id: int | None = None
    context_summary: str | None = None


class PlanCreateRequest(BaseModel):
    conversation_id: int | None = None
    project_id: int | None = None
    reasoning_state_id: int | None = None
    title: str
    goal: str | None = ""
    status: str | None = "draft"


class PlanUpdateRequest(BaseModel):
    conversation_id: int | None = None
    project_id: int | None = None
    reasoning_state_id: int | None = None
    title: str | None = None
    goal: str | None = None
    status: str | None = None


class PlanStepCreateRequest(BaseModel):
    step_order: int
    title: str
    description: str | None = ""
    status: str | None = "pending"
    notes: str | None = ""


class PlanStepUpdateRequest(BaseModel):
    step_order: int | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    notes: str | None = None


class PlanStepDependencyCreateRequest(BaseModel):
    step_id: int
    depends_on_step_id: int


class StepExecutionCreateRequest(BaseModel):
    action_type: str | None = "manual"
    action_payload: dict | None = None
    status: str | None = "pending"
    verification_status: str | None = "unverified"


class StepExecutionUpdateRequest(BaseModel):
    status: str | None = None
    result_summary: str | None = None
    verification_status: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class ToolInputValidationRequest(BaseModel):
    payload: dict


class ToolExecutionRequest(BaseModel):
    payload: dict
    confirmed: bool | None = False
    initiative_mode: str | None = "balanced"
    source_type: str | None = "user"


class ToolPermissionRequest(BaseModel):
    source_type: str
    confirmed: bool | None = False


class ToolAuthorizationRequest(BaseModel):
    confirmed: bool | None = False
    initiative_mode: str | None = "balanced"


class ToolPrecheckRequest(BaseModel):
    payload: dict


class UntrustedTextRequest(BaseModel):
    text: str
    source_type: str | None = "document"


class SecurityScanTextRequest(BaseModel):
    text: str


class SecurityScanStructuredRequest(BaseModel):
    data: dict | list


class TrustAnnotationRequest(BaseModel):
    source_type: str
    item: dict


class AutonomyRunCreateRequest(BaseModel):
    plan_id: int
    reasoning_state_id: int | None = None
    status: str | None = "draft"
    max_steps: int | None = 10
    steps_executed: int | None = 0
    max_tool_calls: int | None = 20
    tool_calls_used: int | None = 0
    stop_reason: str | None = ""


class AutonomyRunUpdateRequest(BaseModel):
    status: str | None = None
    max_steps: int | None = None
    steps_executed: int | None = None
    max_tool_calls: int | None = None
    tool_calls_used: int | None = None
    stop_reason: str | None = None


class RawTextRequest(BaseModel):
    text: str
    source_name: str | None = "manual_input"


class FactUpdateRequest(BaseModel):
    fact_text: str | None = None
    category: str | None = None
    confidence: float | None = None
    visibility: str | None = None
    provenance: str | None = None
    is_pinned: int | None = None


class FactStatusUpdateRequest(BaseModel):
    status: str


class FactSupersedeRequest(BaseModel):
    fact_text: str
    category: str | None = None
    confidence: float | None = 0.9
    visibility: str | None = "personal"
    provenance: str | None = "corrected"
    is_pinned: int | None = 0


class ProjectCreateRequest(BaseModel):
    title: str
    description: str | None = ""
    status: str | None = "active"
    priority: str | None = "medium"


class ProjectUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


class GoalCreateRequest(BaseModel):
    goal_text: str
    project_id: int | None = None
    status: str | None = "active"
    priority: str | None = "medium"
    target_date: str | None = None


class GoalUpdateRequest(BaseModel):
    goal_text: str | None = None
    project_id: int | None = None
    status: str | None = None
    priority: str | None = None
    target_date: str | None = None


class OpenLoopCreateRequest(BaseModel):
    description: str
    project_id: int | None = None
    conversation_id: int | None = None
    status: str | None = "open"
    priority: str | None = "medium"
    due_date: str | None = None


class OpenLoopUpdateRequest(BaseModel):
    description: str | None = None
    project_id: int | None = None
    conversation_id: int | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None


class RecommendationStatusUpdateRequest(BaseModel):
    status: str
    decision_note: str | None = None


class RecommendationGoalPromotionRequest(BaseModel):
    project_id: int | None = None
    priority: str | None = "high"


class RecommendationOpenLoopPromotionRequest(BaseModel):
    project_id: int | None = None
    conversation_id: int | None = None
    priority: str | None = "high"


@app.on_event("startup")
def startup_event():
    init_db()
    consolidation_service.run_startup_consolidation()
    observability_service.log_event("startup_configuration", {
        "app_name": settings.APP_NAME,
        "database_url": settings.DATABASE_URL,
        "background_job_mode": settings.BACKGROUND_JOB_MODE,
        "vector_backend": settings.VECTOR_BACKEND,
        "debug": settings.DEBUG
    })


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "message": "Mnemosyne AI automatic consolidation and evolution is alive."
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "app": settings.APP_NAME,
        "debug": settings.DEBUG
    }


@app.get("/stats")
def get_stats():
    return consolidation_service.get_memory_stats()


@app.get("/facts")
def get_facts():
    return {
        "facts": memory_service.get_all_facts()
    }


@app.get("/facts/active")
def get_active_facts():
    return {
        "facts": memory_service.get_active_facts()
    }


@app.get("/facts/conflicts/check")
def check_fact_conflict(fact_text: str, category: str):
    conflicting = memory_service.find_conflicting_active_fact(fact_text, category)
    return {
        "fact_text": fact_text,
        "category": category,
        "conflict_found": conflicting is not None,
        "conflicting_fact": conflicting
    }


@app.get("/facts/stats")
def get_fact_stats():
    return memory_service.get_fact_stats()


@app.get("/facts/activity")
def get_fact_activity(limit: int = 20):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")
    return {
        "activity": memory_service.get_recent_fact_activity(limit=limit)
    }


@app.get("/facts/status/{status}")
def get_facts_by_status(status: str):
    allowed_statuses = {"active", "superseded", "outdated", "uncertain", "deleted"}
    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status.")

    return {
        "status": status,
        "facts": memory_service.get_facts_by_status(status)
    }


@app.get("/facts/visibility/{visibility}")
def get_facts_by_visibility(visibility: str):
    allowed_visibilities = {"general", "personal", "sensitive", "restricted"}
    if visibility not in allowed_visibilities:
        raise HTTPException(status_code=400, detail="Invalid visibility.")

    return {
        "visibility": visibility,
        "facts": memory_service.get_facts_by_visibility(visibility)
    }


@app.get("/facts/{fact_id}/provenance")
def get_fact_provenance(fact_id: int):
    provenance = memory_service.get_fact_provenance(fact_id)
    if not provenance:
        raise HTTPException(status_code=404, detail="Fact not found.")

    return {
        "fact_id": fact_id,
        "provenance": provenance
    }


@app.get("/facts/{fact_id}")
def get_fact(fact_id: int):
    fact = memory_service.get_fact_by_id(fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")

    return fact


@app.patch("/facts/{fact_id}")
def update_fact(fact_id: int, req: FactUpdateRequest):
    if not memory_service.fact_exists(fact_id):
        raise HTTPException(status_code=404, detail="Fact not found.")

    allowed_visibilities = {"general", "personal", "sensitive", "restricted"}
    allowed_provenances = {"explicit", "inferred", "imported", "corrected"}

    if req.visibility is not None and req.visibility not in allowed_visibilities:
        raise HTTPException(status_code=400, detail="Invalid visibility.")

    if req.provenance is not None and req.provenance not in allowed_provenances:
        raise HTTPException(status_code=400, detail="Invalid provenance.")

    if req.is_pinned is not None and req.is_pinned not in (0, 1):
        raise HTTPException(status_code=400, detail="is_pinned must be 0 or 1.")

    if req.confidence is not None and not (0.0 <= req.confidence <= 1.0):
        raise HTTPException(status_code=400, detail="confidence must be between 0.0 and 1.0.")

    updated = memory_service.update_fact(
        fact_id=fact_id,
        fact_text=req.fact_text,
        category=req.category,
        confidence=req.confidence,
        visibility=req.visibility,
        provenance=req.provenance,
        is_pinned=req.is_pinned
    )

    return {
        "message": "Fact updated successfully.",
        "fact": updated
    }


@app.delete("/facts/{fact_id}")
def delete_fact(fact_id: int):
    deleted = memory_service.soft_delete_fact(fact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fact not found.")

    return {
        "message": "Fact soft-deleted successfully.",
        "fact": deleted
    }


@app.post("/facts/{fact_id}/pin")
def pin_fact(fact_id: int):
    updated = memory_service.pin_fact(fact_id, pinned=True)
    if not updated:
        raise HTTPException(status_code=404, detail="Fact not found.")

    return {
        "message": "Fact pinned successfully.",
        "fact": updated
    }


@app.post("/facts/{fact_id}/unpin")
def unpin_fact(fact_id: int):
    updated = memory_service.pin_fact(fact_id, pinned=False)
    if not updated:
        raise HTTPException(status_code=404, detail="Fact not found.")

    return {
        "message": "Fact unpinned successfully.",
        "fact": updated
    }


@app.post("/facts/{fact_id}/status")
def update_fact_status(fact_id: int, req: FactStatusUpdateRequest):
    allowed_statuses = {"active", "superseded", "outdated", "uncertain", "deleted"}
    if req.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status.")

    try:
        updated = memory_service.mark_fact_status(fact_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Fact not found.")

    return {
        "message": "Fact status updated successfully.",
        "fact": updated
    }


@app.post("/facts/{fact_id}/supersede")
def supersede_fact(fact_id: int, req: FactSupersedeRequest):
    if not req.fact_text.strip():
        raise HTTPException(status_code=400, detail="New fact_text cannot be empty.")

    allowed_visibilities = {"general", "personal", "sensitive", "restricted"}
    allowed_provenances = {"explicit", "inferred", "imported", "corrected"}

    if req.visibility not in allowed_visibilities:
        raise HTTPException(status_code=400, detail="Invalid visibility.")

    if req.provenance not in allowed_provenances:
        raise HTTPException(status_code=400, detail="Invalid provenance.")

    if req.is_pinned not in (0, 1):
        raise HTTPException(status_code=400, detail="is_pinned must be 0 or 1.")

    if req.confidence is not None and not (0.0 <= req.confidence <= 1.0):
        raise HTTPException(status_code=400, detail="confidence must be between 0.0 and 1.0.")

    new_fact = memory_service.supersede_fact(
        old_fact_id=fact_id,
        new_fact_text=req.fact_text,
        category=req.category,
        confidence=req.confidence or 0.9,
        visibility=req.visibility or "personal",
        provenance=req.provenance or "corrected",
        is_pinned=req.is_pinned or 0
    )

    if not new_fact:
        raise HTTPException(status_code=404, detail="Original fact not found.")

    return {
        "message": "Fact superseded successfully.",
        "new_fact": new_fact
    }


@app.get("/facts/history")
def get_fact_history(fact_text: str):
    if not fact_text.strip():
        raise HTTPException(status_code=400, detail="fact_text cannot be empty.")

    history = memory_service.get_fact_history(fact_text)
    return {
        "fact_text": fact_text,
        "history": history
    }


@app.get("/facts/timeline/{kind}")
def get_fact_timeline(kind: str):
    allowed_kinds = {"name", "location_live", "work_role", "work_company"}
    if kind not in allowed_kinds:
        raise HTTPException(status_code=400, detail="Invalid temporal fact kind.")

    return {
        "kind": kind,
        "timeline": memory_service.get_fact_timeline_by_kind(kind)
    }


@app.get("/facts/timelines")
def get_all_temporal_fact_groups():
    return {
        "timelines": memory_service.get_temporal_fact_groups()
    }


@app.get("/temporal/changes")
def get_temporal_changes():
    return {
        "changes": temporal_service.detect_all_changes()
    }


@app.get("/temporal/changes/{kind}")
def get_temporal_change_for_kind(kind: str):
    allowed_kinds = {"name", "location_live", "work_role", "work_company"}
    if kind not in allowed_kinds:
        raise HTTPException(status_code=400, detail="Invalid temporal fact kind.")

    return temporal_service.detect_changes_for_kind(kind)


@app.get("/temporal/health")
def get_temporal_health():
    return temporal_service.get_temporal_health_report()


@app.get("/temporal/stale-facts")
def get_stale_facts(stale_after_days: int = 30):
    if stale_after_days < 1 or stale_after_days > 3650:
        raise HTTPException(status_code=400, detail="stale_after_days must be between 1 and 3650.")

    return {
        "stale_after_days": stale_after_days,
        "stale_facts": temporal_service.detect_stale_facts(stale_after_days=stale_after_days)
    }


@app.get("/temporal/aging-open-loops")
def get_aging_open_loops(stale_after_days: int = 14):
    if stale_after_days < 1 or stale_after_days > 3650:
        raise HTTPException(status_code=400, detail="stale_after_days must be between 1 and 3650.")

    return {
        "stale_after_days": stale_after_days,
        "aging_open_loops": temporal_service.detect_aging_open_loops(stale_after_days=stale_after_days)
    }


@app.get("/temporal/aging-goals")
def get_aging_goals(stale_after_days: int = 21):
    if stale_after_days < 1 or stale_after_days > 3650:
        raise HTTPException(status_code=400, detail="stale_after_days must be between 1 and 3650.")

    return {
        "stale_after_days": stale_after_days,
        "aging_goals": temporal_service.detect_aging_goals(stale_after_days=stale_after_days)
    }


@app.get("/temporal/recurring-open-loops")
def get_recurring_open_loops():
    return {
        "recurring_open_loop_patterns": temporal_service.detect_recurring_open_loop_patterns()
    }


@app.get("/temporal/reconfirmation-candidates")
def get_reconfirmation_candidates(stale_after_days: int = 30):
    if stale_after_days < 1 or stale_after_days > 3650:
        raise HTTPException(status_code=400, detail="stale_after_days must be between 1 and 3650.")

    return {
        "stale_after_days": stale_after_days,
        "reconfirmation_candidates": temporal_service.get_reconfirmation_candidates(
            stale_after_days=stale_after_days
        )
    }


@app.get("/profile")
def get_profile():
    return profile_service.build_profile()


@app.get("/proactive/briefing")
def get_proactive_briefing():
    return proactive_service.generate_proactive_briefing()


@app.get("/proactive/suggestions")
def get_proactive_suggestions(
    conversation_id: int | None = None,
    max_items: int | None = None,
    initiative_mode: str = "balanced"
):
    if initiative_mode not in VALID_INITIATIVE_MODES:
        raise HTTPException(status_code=400, detail="Invalid initiative_mode.")

    if max_items is not None and (max_items < 1 or max_items > 10):
        raise HTTPException(status_code=400, detail="max_items must be between 1 and 10.")

    return initiative_service.get_suggestions_for_chat(
        conversation_id=conversation_id,
        max_items=max_items,
        initiative_mode=initiative_mode
    )


@app.get("/proactive/suggestion-history")
def get_proactive_suggestion_history(limit: int = 50):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "events": initiative_service.list_recent_surface_events(limit=limit)
    }


@app.get("/conversations")
def list_conversations():
    return {
        "conversations": memory_service.list_conversations()
    }


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int):
    if not memory_service.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return {
        "conversation_id": conversation_id,
        "messages": memory_service.get_conversation_messages(conversation_id)
    }


@app.post("/conversations/{conversation_id}/link-project/{project_id}")
def link_conversation_project(conversation_id: int, project_id: int):
    if not memory_service.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if not continuity_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")

    memory_service.link_conversation_to_project(conversation_id, project_id)

    return {
        "message": "Conversation linked to project successfully.",
        "conversation_id": conversation_id,
        "project_id": project_id
    }


@app.get("/projects/{project_id}/conversations")
def get_project_conversations(project_id: int):
    if not continuity_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")

    return {
        "project_id": project_id,
        "conversations": memory_service.get_conversations_by_project(project_id)
    }


@app.get("/memories/search")
def search_memories(query: str):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    results = semantic_memory_service.retrieve_relevant_memories(query)
    return {
        "query": query,
        "results": results
    }


@app.get("/episodes")
def list_episodes():
    return {
        "episodic_memories": evolution_service.list_episodic_memories()
    }


@app.get("/reflections")
def list_reflections():
    return {
        "reflections": evolution_service.list_reflections()
    }


@app.get("/daily-learnings")
def list_daily_learnings():
    return {
        "daily_learnings": evolution_service.list_daily_learnings()
    }


@app.get("/memory-priorities")
def get_memory_priorities():
    return consolidation_service.prioritize_memories()


@app.post("/episodes/create/{conversation_id}")
def create_episode(conversation_id: int):
    if not memory_service.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    result = evolution_service.create_episode_for_conversation(conversation_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/daily-learnings/create")
def create_daily_learning():
    result = evolution_service.create_daily_learning()

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/consolidate")
def run_consolidation():
    results = {
        "facts_consolidated": consolidation_service.consolidate_facts(),
        "daily_learning": consolidation_service.auto_daily_learning()
    }
    return results


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    save_path = DOCS_DIR / file.filename

    content = await file.read()
    save_path.write_bytes(content)

    result = rag_service.add_document_from_path(str(save_path))
    return result


@app.post("/documents/add-text")
def add_text_document(req: RawTextRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    return rag_service.add_raw_text(req.text, req.source_name or "manual_input")


@app.get("/documents/search")
def search_documents(query: str):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    results = rag_service.retrieve_context(query)
    return {
        "query": query,
        "results": results
    }


@app.get("/retrieval/plan")
def get_retrieval_plan(query: str, conversation_id: int | None = None, retrieval_mode: str = "balanced"):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if retrieval_mode not in VALID_RETRIEVAL_MODES:
        raise HTTPException(status_code=400, detail="Invalid retrieval_mode.")

    return retrieval_orchestrator.build_context_package(
        query=query,
        conversation_id=conversation_id,
        retrieval_mode=retrieval_mode
    )


@app.post("/chat")
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    retrieval_mode = req.retrieval_mode or "balanced"
    if retrieval_mode not in VALID_RETRIEVAL_MODES:
        raise HTTPException(status_code=400, detail="Invalid retrieval_mode.")

    initiative_mode = req.initiative_mode or "balanced"
    if initiative_mode not in VALID_INITIATIVE_MODES:
        raise HTTPException(status_code=400, detail="Invalid initiative_mode.")

    chat_mode = req.mode or "standard"
    if chat_mode not in VALID_CHAT_MODES:
        raise HTTPException(status_code=400, detail="Invalid mode. Use: fast, standard, deep.")

    is_fast = chat_mode == "fast"

    if req.conversation_id is not None:
        if not memory_service.conversation_exists(req.conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found.")
        conversation_id = req.conversation_id
    else:
        conversation_id = memory_service.create_conversation(title="Chat Session")

    existing_project_id = memory_service.get_conversation_project_id(conversation_id)

    inferred_project = continuity_service.infer_project_for_message(
        message=req.message,
        conversation_project_id=existing_project_id
    )

    active_project_id = inferred_project["id"] if inferred_project else existing_project_id

    user_message_id = memory_service.save_message(
        conversation_id=conversation_id,
        role="user",
        content=req.message
    )

    semantic_memory_service.store_message_memory(
        conversation_id=conversation_id,
        message_id=user_message_id,
        role="user",
        content=req.message
    )

    extracted_facts = memory_service.extract_and_store_facts(
        conversation_id=conversation_id,
        user_message=req.message,
        source_message_id=user_message_id
    )

    if is_fast:
        extracted_continuity = {}
        stored_continuity = {}
    else:
        extracted_continuity = continuity_extractor.extract(req.message)
        stored_continuity = continuity_service.auto_store_extracted_items(
            extracted=extracted_continuity,
            conversation_id=conversation_id,
            project_id=active_project_id
        )

        if stored_continuity.get("effective_project_id") and existing_project_id != stored_continuity["effective_project_id"]:
            active_project_id = stored_continuity["effective_project_id"]
            memory_service.link_conversation_to_project(conversation_id, active_project_id)
        elif active_project_id is not None and existing_project_id != active_project_id:
            memory_service.link_conversation_to_project(conversation_id, active_project_id)

    effective_retrieval_mode = "focused" if is_fast else retrieval_mode

    context_package = retrieval_orchestrator.build_context_package(
        query=req.message,
        conversation_id=conversation_id,
        retrieval_mode=effective_retrieval_mode,
        active_project_id=active_project_id
    )

    observability_service.log_retrieval_context(
        conversation_id=conversation_id,
        context_package=context_package
    )

    observability_service.log_memory_extraction(
        conversation_id=conversation_id,
        facts_extracted_count=len(extracted_facts),
        continuity_summary=stored_continuity
    )

    recent_messages = context_package["recent_messages"]
    retrieved_contexts = context_package["retrieved_contexts"]
    retrieved_memories = context_package["retrieved_memories"]
    facts = context_package["facts"]
    profile_summary = context_package["profile_summary"]
    query_type = context_package["query_type"]
    continuity_context = context_package["continuity"]
    reflection_context = context_package["reflections"]
    temporal_context = context_package["temporal"]
    proactive_context = context_package["proactive"]
    reasoning_context = context_package["reasoning"]
    is_temporal_query = context_package["is_temporal_query"]
    is_proactive_query = context_package["is_proactive_query"]

    model = routing_service.choose_model(req.message)

    built_system_prompt = prompt_builder.build_system_prompt(
        base_system_prompt=req.system_prompt,
        profile_summary=profile_summary,
        facts=facts,
        retrieved_contexts=retrieved_contexts,
        retrieved_memories=retrieved_memories,
        continuity=continuity_context,
        reflections=reflection_context,
        temporal=temporal_context,
        proactive=proactive_context,
        reasoning=reasoning_context,
        query_type=query_type
    )

    try:
        result = llm_service.chat(
            model=model,
            messages=[
                {"role": "system", "content": built_system_prompt},
                *[
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in recent_messages
                    if msg["role"] in ("user", "assistant")
                ]
            ],
            temperature=0.7
        )
    except OpenRouterError as e:
        observability_service.log_error(
            event_type="chat_llm_error",
            error=str(e),
            extra={
                "conversation_id": conversation_id,
                "query_type": query_type,
                "retrieval_mode": retrieval_mode
            }
        )
        raise HTTPException(status_code=500, detail=str(e))

    observability_service.log_chat_request(
        conversation_id=conversation_id,
        query_type=query_type,
        retrieval_mode=retrieval_mode,
        model_used=result["model"]
    )

    assistant_message_id = memory_service.save_message(
        conversation_id=conversation_id,
        role="assistant",
        content=result["content"],
        model_used=result["model"]
    )

    semantic_memory_service.store_message_memory(
        conversation_id=conversation_id,
        message_id=assistant_message_id,
        role="assistant",
        content=result["content"]
    )

    consolidation_job = job_service.schedule(
        background_tasks,
        safe_background_consolidation,
        conversation_id
    )

    return {
        "conversation_id": conversation_id,
        "reply": result["content"],
        "model_used": result["model"],
        "usage": result["usage"],
        "mode": chat_mode,
        "facts_extracted": extracted_facts,
        "recent_messages_count": len(recent_messages),
        "memory_summary_used": profile_summary,
        "retrieved_contexts": retrieved_contexts,
        "retrieved_memories": retrieved_memories,
        "consolidation": consolidation_job,
        "query_type": query_type,
        "retrieval_mode": context_package["retrieval_mode"],
        "mode_effects": context_package["mode_effects"],
        "retrieval_plan": context_package["retrieval_plan"],
        "retrieval_trace": context_package["retrieval_trace"],
        "context_counts": context_package["context_counts"],
        "budget_profile": context_package["budget_profile"],
        "context_usage": context_package["context_usage"],
        "continuity_extracted": extracted_continuity,
        "continuity_stored": stored_continuity,
        "continuity_context_used": continuity_context,
        "reflection_context_used": reflection_context,
        "is_temporal_query": is_temporal_query,
        "temporal_context_used": temporal_context,
        "is_proactive_query": is_proactive_query,
        "proactive_context_used": proactive_context,
        "reasoning_context_used": reasoning_context,
        "active_project_id": active_project_id,
        "conversation_project_id": memory_service.get_conversation_project_id(conversation_id),
        "initiative_mode": initiative_mode,
        "pending_memory_suggestions": recommendation_service.get_top_pending_recommendations(
            limit=3,
            min_score=1.0
        ),
        "initiative_suggestions": initiative_service.get_suggestions_for_chat(
            conversation_id=conversation_id,
            initiative_mode=initiative_mode
        ),
        "summary": _build_chat_summary(
            query_type=query_type,
            chat_mode=chat_mode,
            effective_retrieval_mode=effective_retrieval_mode,
            facts=facts,
            retrieved_memories=retrieved_memories,
            retrieved_contexts=retrieved_contexts,
            continuity_context=continuity_context,
            reasoning_context=reasoning_context,
            result=result
        )
    }


def _build_chat_summary(
    query_type: str,
    chat_mode: str,
    effective_retrieval_mode: str,
    facts: list,
    retrieved_memories: list,
    retrieved_contexts: list,
    continuity_context: dict,
    reasoning_context: dict,
    result: dict
) -> dict:
    query_type_human = {
        "personal_memory": "your personal memories",
        "document_qa": "documents you uploaded",
        "project_continuity": "your projects and goals",
        "knowledge_plus_memory": "your memories and documents together",
        "general_chat": "your past conversations"
    }.get(query_type, "your conversation history")

    projects = continuity_context.get("projects", [])
    project_names = [p.get("title", "") for p in projects if p.get("title")]

    what_it_did = f"I used {query_type_human} to answer your question"

    if project_names:
        what_it_did += f", drawing from your project(s): {', '.join(project_names[:2])}"
        if len(project_names) > 2:
            what_it_did += f" and {len(project_names) - 2} more"
    elif len(facts) > 0:
        what_it_did += f", drawing on {len(facts)} things I know about you"

    if len(retrieved_contexts) > 0:
        what_it_did += f" and {len(retrieved_contexts)} document(s)"

    what_it_did += "."

    fast_mode_warning = None
    if chat_mode == "fast":
        fast_mode_warning = "Fast mode was used. I skipped deep analysis to respond quickly. The answer may be less thorough than usual."

    reasoning_quality = None
    states = reasoning_context.get("states", [])
    if states:
        top = states[0]
        quality = top.get("_quality", {})
        confidence_label = quality.get("confidence_label", "unknown")
        if confidence_label == "low":
            reasoning_quality = "I'm not fully confident in this answer and may need more information to do better."
        elif confidence_label == "medium":
            reasoning_quality = "I'm fairly confident, but some aspects may need verification."

    return {
        "what_it_did": what_it_did,
        "query_type": query_type,
        "mode": chat_mode,
        "retrieval_mode": effective_retrieval_mode,
        "facts_used": len(facts),
        "memories_used": len(retrieved_memories),
        "documents_used": len(retrieved_contexts),
        "continuity_items": len(projects),
        "project_names": project_names,
        "model": result["model"],
        "token_usage": result["usage"],
        "fast_mode_warning": fast_mode_warning,
        "reasoning_quality": reasoning_quality
    }


@app.post("/projects")
def create_project(req: ProjectCreateRequest):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Project title cannot be empty.")
    if req.status not in VALID_PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid project status.")
    if req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")

    project_id = continuity_service.create_project(
        title=req.title,
        description=req.description or "",
        status=req.status or "active",
        priority=req.priority or "medium"
    )

    return {
        "message": "Project created successfully.",
        "project": continuity_service.get_project_by_id(project_id)
    }


@app.get("/projects")
def list_projects(status: str | None = None):
    if status is not None and status not in VALID_PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid project status.")

    return {
        "projects": continuity_service.list_projects(status=status)
    }


@app.get("/projects/{project_id}")
def get_project(project_id: int):
    project = continuity_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return project


@app.patch("/projects/{project_id}")
def update_project(project_id: int, req: ProjectUpdateRequest):
    if req.status is not None and req.status not in VALID_PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid project status.")
    if req.priority is not None and req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")

    updated = continuity_service.update_project(
        project_id=project_id,
        title=req.title,
        description=req.description,
        status=req.status,
        priority=req.priority
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Project not found.")

    return {
        "message": "Project updated successfully.",
        "project": updated
    }


@app.post("/goals")
def create_goal(req: GoalCreateRequest):
    if not req.goal_text.strip():
        raise HTTPException(status_code=400, detail="Goal text cannot be empty.")
    if req.status not in VALID_GOAL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid goal status.")
    if req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")
    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    goal_id = continuity_service.create_goal(
        goal_text=req.goal_text,
        project_id=req.project_id,
        status=req.status or "active",
        priority=req.priority or "medium",
        target_date=req.target_date
    )

    return {
        "message": "Goal created successfully.",
        "goal": continuity_service.get_goal_by_id(goal_id)
    }


@app.get("/goals")
def list_goals(status: str | None = None, project_id: int | None = None):
    if status is not None and status not in VALID_GOAL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid goal status.")
    if project_id is not None and not continuity_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    return {
        "goals": continuity_service.list_goals(status=status, project_id=project_id)
    }


@app.get("/goals/{goal_id}")
def get_goal(goal_id: int):
    goal = continuity_service.get_goal_by_id(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    return goal


@app.patch("/goals/{goal_id}")
def update_goal(goal_id: int, req: GoalUpdateRequest):
    if req.status is not None and req.status not in VALID_GOAL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid goal status.")
    if req.priority is not None and req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")
    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    updated = continuity_service.update_goal(
        goal_id=goal_id,
        goal_text=req.goal_text,
        project_id=req.project_id,
        status=req.status,
        priority=req.priority,
        target_date=req.target_date
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Goal not found.")

    return {
        "message": "Goal updated successfully.",
        "goal": updated
    }


@app.post("/open-loops")
def create_open_loop(req: OpenLoopCreateRequest):
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="Open loop description cannot be empty.")
    if req.status not in VALID_OPEN_LOOP_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid open loop status.")
    if req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")
    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")
    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    loop_id = continuity_service.create_open_loop(
        description=req.description,
        project_id=req.project_id,
        conversation_id=req.conversation_id,
        status=req.status or "open",
        priority=req.priority or "medium",
        due_date=req.due_date
    )

    return {
        "message": "Open loop created successfully.",
        "open_loop": continuity_service.get_open_loop_by_id(loop_id)
    }


@app.get("/open-loops")
def list_open_loops(
    status: str | None = None,
    project_id: int | None = None,
    conversation_id: int | None = None
):
    if status is not None and status not in VALID_OPEN_LOOP_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid open loop status.")
    if project_id is not None and not continuity_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")
    if conversation_id is not None and not memory_service.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    return {
        "open_loops": continuity_service.list_open_loops(
            status=status,
            project_id=project_id,
            conversation_id=conversation_id
        )
    }


@app.get("/open-loops/{loop_id}")
def get_open_loop(loop_id: int):
    open_loop = continuity_service.get_open_loop_by_id(loop_id)
    if not open_loop:
        raise HTTPException(status_code=404, detail="Open loop not found.")

    return open_loop


@app.patch("/open-loops/{loop_id}")
def update_open_loop(loop_id: int, req: OpenLoopUpdateRequest):
    if req.status is not None and req.status not in VALID_OPEN_LOOP_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid open loop status.")
    if req.priority is not None and req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")
    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")
    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    updated = continuity_service.update_open_loop(
        loop_id=loop_id,
        description=req.description,
        project_id=req.project_id,
        conversation_id=req.conversation_id,
        status=req.status,
        priority=req.priority,
        due_date=req.due_date
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Open loop not found.")

    return {
        "message": "Open loop updated successfully.",
        "open_loop": updated
    }


@app.get("/continuity/snapshot")
def get_continuity_snapshot():
    return continuity_service.get_continuity_snapshot()


@app.get("/continuity/next-actions")
def get_continuity_next_actions(limit: int = 8):
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50.")

    return {
        "next_actions": continuity_service.suggest_next_actions(limit=limit)
    }


@app.get("/weekly-learnings")
def list_weekly_learnings():
    return {
        "weekly_learnings": evolution_service.list_weekly_learnings()
    }


@app.post("/weekly-learnings/create")
def create_weekly_learning():
    result = evolution_service.create_weekly_learning()

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.get("/evals/run")
def run_evaluations():
    return evaluation_service.run_all_evaluations()


@app.get("/evals/{category}")
def run_eval_category(category: str):
    mapping = {
        "fact_recall": evaluation_service.evaluate_fact_recall,
        "contradiction_state": evaluation_service.evaluate_contradiction_state,
        "continuity_state": evaluation_service.evaluate_continuity_state,
        "retrieval_modes": evaluation_service.evaluate_retrieval_modes,
        "reflection_coverage": evaluation_service.evaluate_reflection_coverage,
    }

    if category not in mapping:
        raise HTTPException(status_code=404, detail="Unknown evaluation category.")

    return mapping[category]()


@app.get("/memory-recommendations")
def list_memory_recommendations(
    status: str | None = None,
    category: str | None = None,
    limit: int = 100
):
    allowed_statuses = {"proposed", "accepted", "rejected", "promoted"}
    allowed_categories = {"memory_candidate", "user_insight", "preference", "project", "goal", "conflict_note"}

    if status is not None and status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid recommendation status.")

    if category is not None and category not in allowed_categories:
        raise HTTPException(status_code=400, detail="Invalid recommendation category.")

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "recommendations": recommendation_service.list_recommendations(
            status=status,
            category=category,
            limit=limit
        )
    }


@app.post("/memory-recommendations/generate")
def generate_memory_recommendations(limit: int = 20):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")

    return recommendation_service.generate_from_reflections(limit=limit)


@app.get("/memory-recommendations/candidates")
def get_memory_recommendation_candidates(
    status: str = "proposed",
    limit: int = 20
):
    allowed_statuses = {"proposed", "accepted", "rejected", "promoted"}

    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid recommendation status.")

    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")

    return recommendation_service.get_top_candidates(status=status, limit=limit)


@app.get("/memory-recommendations/review-queue")
def get_memory_recommendation_review_queue(limit: int = 25):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")

    return recommendation_service.get_review_queue(limit=limit)


@app.get("/memory-recommendations/top-pending")
def get_top_pending_memory_recommendations(limit: int = 5, min_score: float = 0.9):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100.")

    if min_score < 0.0 or min_score > 2.0:
        raise HTTPException(status_code=400, detail="min_score must be between 0.0 and 2.0.")

    return recommendation_service.get_top_pending_recommendations(
        limit=limit,
        min_score=min_score
    )


@app.patch("/memory-recommendations/{recommendation_id}/status")
def update_memory_recommendation_status(
    recommendation_id: int,
    req: RecommendationStatusUpdateRequest
):
    allowed_statuses = {"proposed", "accepted", "rejected", "promoted"}

    if req.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid recommendation status.")

    try:
        updated = recommendation_service.update_recommendation_status(
            recommendation_id=recommendation_id,
            new_status=req.status,
            decision_note=req.decision_note
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return {
        "message": "Recommendation status updated successfully.",
        "recommendation": updated
    }


@app.post("/memory-recommendations/{recommendation_id}/accept")
def accept_memory_recommendation(
    recommendation_id: int,
    decision_note: str | None = None
):
    try:
        updated = recommendation_service.accept_recommendation(
            recommendation_id=recommendation_id,
            decision_note=decision_note
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return {
        "message": "Recommendation accepted successfully.",
        "recommendation": updated
    }


@app.post("/memory-recommendations/{recommendation_id}/reject")
def reject_memory_recommendation(
    recommendation_id: int,
    decision_note: str | None = None
):
    try:
        updated = recommendation_service.reject_recommendation(
            recommendation_id=recommendation_id,
            decision_note=decision_note
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return {
        "message": "Recommendation rejected successfully.",
        "recommendation": updated
    }


@app.post("/memory-recommendations/{recommendation_id}/promote")
def promote_memory_recommendation(
    recommendation_id: int,
    pin: bool = True
):
    try:
        result = recommendation_service.promote_recommendation_to_fact(
            recommendation_id=recommendation_id,
            pin=pin
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return {
        "message": "Recommendation promoted successfully.",
        "result": result
    }


@app.post("/memory-recommendations/{recommendation_id}/promote-goal")
def promote_memory_recommendation_to_goal(
    recommendation_id: int,
    req: RecommendationGoalPromotionRequest
):
    if req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")

    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    try:
        result = recommendation_service.promote_recommendation_to_goal(
            recommendation_id=recommendation_id,
            project_id=req.project_id,
            priority=req.priority or "high"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return {
        "message": "Recommendation promoted to goal successfully.",
        "result": result
    }


@app.post("/memory-recommendations/{recommendation_id}/promote-open-loop")
def promote_memory_recommendation_to_open_loop(
    recommendation_id: int,
    req: RecommendationOpenLoopPromotionRequest
):
    if req.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")

    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    try:
        result = recommendation_service.promote_recommendation_to_open_loop(
            recommendation_id=recommendation_id,
            project_id=req.project_id,
            conversation_id=req.conversation_id,
            priority=req.priority or "high"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return {
        "message": "Recommendation promoted to open loop successfully.",
        "result": result
    }


@app.get("/memory-recommendations/{recommendation_id}")
def get_memory_recommendation(recommendation_id: int):
    recommendation = recommendation_service.get_recommendation_by_id(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    return recommendation


@app.post("/reasoning-states")
def create_reasoning_state(req: ReasoningStateCreateRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="task cannot be empty.")

    if req.status not in VALID_REASONING_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid reasoning state status.")

    if req.confidence is not None and not (0.0 <= req.confidence <= 1.0):
        raise HTTPException(status_code=400, detail="confidence must be between 0.0 and 1.0.")

    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    reasoning_id = reasoning_service.create_reasoning_state(
        conversation_id=req.conversation_id,
        project_id=req.project_id,
        task=req.task,
        goal=req.goal or "",
        constraints=req.constraints or [],
        assumptions=req.assumptions or [],
        candidate_actions=req.candidate_actions or [],
        selected_action=req.selected_action,
        confidence=req.confidence if req.confidence is not None else 0.5,
        self_check=req.self_check or {},
        status=req.status or "draft"
    )

    return {
        "message": "Reasoning state created successfully.",
        "reasoning_state": reasoning_service.get_reasoning_state_by_id(reasoning_id)
    }


@app.get("/reasoning-states")
def list_reasoning_states(
    status: str | None = None,
    conversation_id: int | None = None,
    project_id: int | None = None,
    limit: int = 100
):
    if status is not None and status not in VALID_REASONING_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid reasoning state status.")

    if conversation_id is not None and not memory_service.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    if project_id is not None and not continuity_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "reasoning_states": reasoning_service.list_reasoning_states(
            status=status,
            conversation_id=conversation_id,
            project_id=project_id,
            limit=limit
        )
    }


@app.post("/reasoning-states/generate")
def generate_reasoning_state(req: ReasoningStateGenerateRequest):
    if not req.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input cannot be empty.")

    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    try:
        reasoning_state = reasoning_service.generate_reasoning_state_from_input(
            user_input=req.user_input,
            conversation_id=req.conversation_id,
            project_id=req.project_id,
            context_summary=req.context_summary
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reasoning generation failed: {str(e)}")

    return {
        "message": "Reasoning state generated successfully.",
        "reasoning_state": reasoning_state,
        "validation": reasoning_service.validate_reasoning_payload(reasoning_state)
    }


@app.get("/reasoning-states/{reasoning_id}/validate")
def validate_reasoning_state(reasoning_id: int):
    validation = reasoning_service.validate_reasoning_state(reasoning_id)
    if not validation:
        raise HTTPException(status_code=404, detail="Reasoning state not found.")

    return validation


@app.get("/reasoning-states/{reasoning_id}/quality")
def get_reasoning_state_quality(reasoning_id: int):
    report = reasoning_service.get_reasoning_quality_report(reasoning_id)
    if not report:
        raise HTTPException(status_code=404, detail="Reasoning state not found.")

    return report


@app.get("/reasoning-states/{reasoning_id}")
def get_reasoning_state(reasoning_id: int):
    state = reasoning_service.get_reasoning_state_by_id(reasoning_id)
    if not state:
        raise HTTPException(status_code=404, detail="Reasoning state not found.")

    return state


@app.patch("/reasoning-states/{reasoning_id}")
def update_reasoning_state(reasoning_id: int, req: ReasoningStateUpdateRequest):
    if req.status is not None and req.status not in VALID_REASONING_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid reasoning state status.")

    if req.confidence is not None and not (0.0 <= req.confidence <= 1.0):
        raise HTTPException(status_code=400, detail="confidence must be between 0.0 and 1.0.")

    updated = reasoning_service.update_reasoning_state(
        reasoning_id=reasoning_id,
        task=req.task,
        goal=req.goal,
        constraints=req.constraints,
        assumptions=req.assumptions,
        candidate_actions=req.candidate_actions,
        selected_action=req.selected_action,
        confidence=req.confidence,
        self_check=req.self_check,
        status=req.status
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Reasoning state not found.")

    return {
        "message": "Reasoning state updated successfully.",
        "reasoning_state": updated
    }


@app.post("/plans")
def create_plan(req: PlanCreateRequest):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Plan title cannot be empty.")

    if req.status not in VALID_PLAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid plan status.")

    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    if req.reasoning_state_id is not None and not reasoning_service.reasoning_state_exists(req.reasoning_state_id):
        raise HTTPException(status_code=404, detail="Linked reasoning state not found.")

    plan_id = planning_service.create_plan(
        conversation_id=req.conversation_id,
        project_id=req.project_id,
        reasoning_state_id=req.reasoning_state_id,
        title=req.title,
        goal=req.goal or "",
        status=req.status or "draft"
    )

    return {
        "message": "Plan created successfully.",
        "plan": planning_service.get_plan_by_id(plan_id)
    }


@app.get("/plans")
def list_plans(
    status: str | None = None,
    conversation_id: int | None = None,
    project_id: int | None = None,
    reasoning_state_id: int | None = None,
    limit: int = 100
):
    if status is not None and status not in VALID_PLAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid plan status.")

    if conversation_id is not None and not memory_service.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    if project_id is not None and not continuity_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    if reasoning_state_id is not None and not reasoning_service.reasoning_state_exists(reasoning_state_id):
        raise HTTPException(status_code=404, detail="Linked reasoning state not found.")

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "plans": planning_service.list_plans(
            status=status,
            conversation_id=conversation_id,
            project_id=project_id,
            reasoning_state_id=reasoning_state_id,
            limit=limit
        )
    }


@app.post("/plans/generate-from-reasoning/{reasoning_state_id}")
def generate_plan_from_reasoning(reasoning_state_id: int):
    if not reasoning_service.reasoning_state_exists(reasoning_state_id):
        raise HTTPException(status_code=404, detail="Reasoning state not found.")

    try:
        result = planning_service.generate_plan_from_reasoning_state(reasoning_state_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")

    return {
        "message": "Plan generated successfully from reasoning state.",
        "result": result
    }


@app.get("/plans/{plan_id}/summary")
def get_plan_summary(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    summary = planning_service.get_plan_progress_summary(plan_id)
    return summary


@app.get("/plans/{plan_id}/health")
def get_plan_health(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    health = planning_service.get_plan_health_summary(plan_id)
    return health


@app.get("/plans/{plan_id}/execution-health")
def get_plan_execution_health(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    health = planning_service.get_plan_execution_health_summary(plan_id)
    return health


@app.get("/plans/{plan_id}")
def get_plan(plan_id: int):
    plan = planning_service.get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    return plan


@app.patch("/plans/{plan_id}")
def update_plan(plan_id: int, req: PlanUpdateRequest):
    if req.status is not None and req.status not in VALID_PLAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid plan status.")

    if req.conversation_id is not None and not memory_service.conversation_exists(req.conversation_id):
        raise HTTPException(status_code=404, detail="Linked conversation not found.")

    if req.project_id is not None and not continuity_service.project_exists(req.project_id):
        raise HTTPException(status_code=404, detail="Linked project not found.")

    if req.reasoning_state_id is not None and not reasoning_service.reasoning_state_exists(req.reasoning_state_id):
        raise HTTPException(status_code=404, detail="Linked reasoning state not found.")

    updated = planning_service.update_plan(
        plan_id=plan_id,
        conversation_id=req.conversation_id,
        project_id=req.project_id,
        reasoning_state_id=req.reasoning_state_id,
        title=req.title,
        goal=req.goal,
        status=req.status
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Plan not found.")

    return {
        "message": "Plan updated successfully.",
        "plan": updated
    }


@app.post("/plans/{plan_id}/steps")
def create_plan_step(plan_id: int, req: PlanStepCreateRequest):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Step title cannot be empty.")

    if req.status not in VALID_PLAN_STEP_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid plan step status.")

    if req.step_order < 1:
        raise HTTPException(status_code=400, detail="step_order must be >= 1.")

    step_id = planning_service.create_plan_step(
        plan_id=plan_id,
        step_order=req.step_order,
        title=req.title,
        description=req.description or "",
        status=req.status or "pending",
        notes=req.notes or ""
    )

    return {
        "message": "Plan step created successfully.",
        "step": planning_service.get_plan_step_by_id(step_id)
    }


@app.get("/plans/{plan_id}/steps")
def list_plan_steps(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    return {
        "plan_id": plan_id,
        "steps": planning_service.list_plan_steps(plan_id)
    }


@app.patch("/plan-steps/{step_id}")
def update_plan_step(step_id: int, req: PlanStepUpdateRequest):
    if req.status is not None and req.status not in VALID_PLAN_STEP_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid plan step status.")

    if req.step_order is not None and req.step_order < 1:
        raise HTTPException(status_code=400, detail="step_order must be >= 1.")

    updated = planning_service.update_plan_step(
        step_id=step_id,
        step_order=req.step_order,
        title=req.title,
        description=req.description,
        status=req.status,
        notes=req.notes
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Plan step not found.")

    return {
        "message": "Plan step updated successfully.",
        "step": updated
    }


@app.post("/plans/{plan_id}/dependencies")
def add_plan_step_dependency(plan_id: int, req: PlanStepDependencyCreateRequest):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    try:
        dep_id = planning_service.add_step_dependency(
            plan_id=plan_id,
            step_id=req.step_id,
            depends_on_step_id=req.depends_on_step_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if dep_id is None:
        raise HTTPException(status_code=404, detail="One or both referenced steps not found.")

    return {
        "message": "Dependency added successfully.",
        "dependency_id": dep_id
    }


@app.get("/plans/{plan_id}/dependencies")
def list_plan_dependencies(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    return {
        "plan_id": plan_id,
        "dependencies": planning_service.list_step_dependencies(plan_id)
    }


@app.get("/plans/{plan_id}/blocked-steps")
def get_blocked_plan_steps(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    return {
        "plan_id": plan_id,
        "blocked_steps": planning_service.get_blocked_steps(plan_id)
    }


@app.get("/plans/{plan_id}/ready-steps")
def get_ready_plan_steps(plan_id: int):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    return {
        "plan_id": plan_id,
        "ready_steps": planning_service.get_ready_steps(plan_id)
    }


@app.post("/plans/{plan_id}/steps/{step_id}/executions")
def create_step_execution(plan_id: int, step_id: int, req: StepExecutionCreateRequest):
    if not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    step = planning_service.get_plan_step_by_id(step_id)
    if not step or step["plan_id"] != plan_id:
        raise HTTPException(status_code=404, detail="Step not found for this plan.")

    if req.status not in VALID_EXECUTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid execution status.")

    if req.verification_status not in VALID_VERIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid verification status.")

    execution_id = execution_service.create_step_execution(
        plan_id=plan_id,
        step_id=step_id,
        action_type=req.action_type or "manual",
        action_payload=req.action_payload or {},
        status=req.status or "pending",
        verification_status=req.verification_status or "unverified"
    )

    return {
        "message": "Step execution created successfully.",
        "execution": execution_service.get_step_execution_by_id(execution_id)
    }


@app.get("/step-executions")
def list_step_executions(
    plan_id: int | None = None,
    step_id: int | None = None,
    status: str | None = None,
    verification_status: str | None = None,
    limit: int = 100
):
    if plan_id is not None and not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found.")

    if step_id is not None and not planning_service.plan_step_exists(step_id):
        raise HTTPException(status_code=404, detail="Step not found.")

    if status is not None and status not in VALID_EXECUTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid execution status.")

    if verification_status is not None and verification_status not in VALID_VERIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid verification status.")

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "executions": execution_service.list_step_executions(
            plan_id=plan_id,
            step_id=step_id,
            status=status,
            verification_status=verification_status,
            limit=limit
        )
    }


@app.get("/step-executions/{execution_id}")
def get_step_execution(execution_id: int):
    execution = execution_service.get_step_execution_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return execution


@app.patch("/step-executions/{execution_id}")
def update_step_execution(execution_id: int, req: StepExecutionUpdateRequest):
    if req.status is not None and req.status not in VALID_EXECUTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid execution status.")

    if req.verification_status is not None and req.verification_status not in VALID_VERIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid verification status.")

    updated = execution_service.update_step_execution(
        execution_id=execution_id,
        status=req.status,
        result_summary=req.result_summary,
        verification_status=req.verification_status,
        error_message=req.error_message,
        started_at=req.started_at,
        finished_at=req.finished_at
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return {
        "message": "Step execution updated successfully.",
        "execution": updated
    }


@app.post("/step-executions/{execution_id}/start")
def start_step_execution(execution_id: int):
    try:
        execution = execution_service.start_execution(execution_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return {"message": "Execution started.", "execution": execution}


@app.post("/step-executions/{execution_id}/succeed")
def succeed_step_execution(execution_id: int, result_summary: str = ""):
    try:
        execution = execution_service.mark_execution_succeeded(execution_id, result_summary=result_summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return {"message": "Execution marked succeeded.", "execution": execution}


@app.post("/step-executions/{execution_id}/fail")
def fail_step_execution(execution_id: int, error_message: str = "", result_summary: str = ""):
    try:
        execution = execution_service.mark_execution_failed(
            execution_id=execution_id,
            error_message=error_message,
            result_summary=result_summary
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return {"message": "Execution marked failed.", "execution": execution}


@app.post("/step-executions/{execution_id}/verify")
def verify_step_execution(execution_id: int):
    try:
        execution = execution_service.mark_execution_verified(execution_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return {"message": "Execution marked verified.", "execution": execution}


@app.post("/step-executions/{execution_id}/sync-step")
def sync_step_from_execution(execution_id: int):
    result = execution_service.sync_step_status_from_execution(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution or linked step not found.")

    return {
        "message": "Step synchronized from execution successfully.",
        "result": result
    }


@app.get("/step-executions/{execution_id}/recovery")
def get_step_execution_recovery(execution_id: int):
    recommendation = execution_service.get_execution_recovery_recommendation(execution_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Execution not found.")

    return recommendation


@app.post("/step-executions/{execution_id}/retry")
def retry_step_execution(execution_id: int):
    recovery = execution_service.get_execution_recovery_recommendation(execution_id)
    if not recovery:
        raise HTTPException(status_code=404, detail="Execution not found.")

    if not recovery["can_retry"]:
        raise HTTPException(status_code=400, detail="Execution is not eligible for retry.")

    original = execution_service.get_step_execution_by_id(execution_id)
    new_execution_id = execution_service.create_step_execution(
        plan_id=original["plan_id"],
        step_id=original["step_id"],
        action_type=original["action_type"],
        action_payload=original["action_payload"],
        status="pending",
        verification_status="unverified"
    )

    return {
        "message": "Retry execution created successfully.",
        "execution": execution_service.get_step_execution_by_id(new_execution_id)
    }


@app.get("/tools")
def list_tools(enabled_only: bool = False):
    tools = (
        tool_registry_service.list_enabled_tools()
        if enabled_only
        else tool_registry_service.list_tools()
    )
    return {"tools": tools}


@app.get("/tools/{tool_name}")
def get_tool(tool_name: str):
    tool = tool_registry_service.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found.")

    return tool


@app.post("/tools/{tool_name}/validate-input")
def validate_tool_input(tool_name: str, req: ToolInputValidationRequest):
    result = tool_registry_service.validate_tool_input(
        tool_name=tool_name,
        payload=req.payload
    )

    return result


@app.post("/tools/{tool_name}/execute")
def execute_tool(tool_name: str, req: ToolExecutionRequest):
    initiative_mode = req.initiative_mode or "balanced"
    if initiative_mode not in VALID_INITIATIVE_MODES:
        raise HTTPException(status_code=400, detail="Invalid initiative_mode.")

    source_type = req.source_type or "user"

    result = tool_execution_service.execute_tool(
        tool_name=tool_name,
        payload=req.payload,
        confirmed=req.confirmed or False,
        initiative_mode=initiative_mode,
        source_type=source_type
    )
    return result


@app.post("/tools/{tool_name}/authorize")
def authorize_tool(tool_name: str, req: ToolAuthorizationRequest):
    initiative_mode = req.initiative_mode or "balanced"
    if initiative_mode not in VALID_INITIATIVE_MODES:
        raise HTTPException(status_code=400, detail="Invalid initiative_mode.")

    result = tool_policy_service.authorize_tool_use(
        tool_name=tool_name,
        confirmed=req.confirmed or False,
        initiative_mode=initiative_mode
    )

    return result


@app.post("/tools/{tool_name}/precheck")
def precheck_tool(tool_name: str, req: ToolPrecheckRequest):
    return tool_control_service.precheck_tool_invocation(
        tool_name=tool_name,
        payload=req.payload
    )


@app.get("/tools/invocations")
def list_tool_invocations(tool_name: str | None = None, limit: int = 50):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "invocations": tool_control_service.list_recent_tool_invocations(
            tool_name=tool_name,
            limit=limit
        )
    }


@app.get("/trust/sources")
def list_trust_sources():
    return {
        "sources": [
            trust_service.classify_source("system"),
            trust_service.classify_source("user"),
            trust_service.classify_source("memory"),
            trust_service.classify_source("document"),
            trust_service.classify_source("tool_output"),
            trust_service.classify_source("external")
        ]
    }


@app.get("/trust/sources/{source_type}")
def get_trust_source(source_type: str):
    return trust_service.classify_source(source_type)


@app.post("/trust/isolate")
def isolate_untrusted_text(req: UntrustedTextRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty.")

    result = prompt_security_service.isolate_untrusted_text(
        req.text,
        source_type=req.source_type or "document"
    )

    detection = prompt_security_service.detect_suspicious_content(req.text)

    return {
        "isolated_text": result,
        "detection": detection
    }


@app.post("/tools/{tool_name}/check-permission")
def check_tool_permission(tool_name: str, req: ToolPermissionRequest):
    result = permission_service.check_tool_permission(
        tool_name=tool_name,
        source_type=req.source_type,
        confirmed=req.confirmed or False
    )
    return result


@app.post("/security/scan-output")
def scan_output(req: SecurityScanTextRequest):
    return security_scan_service.scan_text(req.text)


@app.post("/security/redact-output")
def redact_output(req: SecurityScanTextRequest):
    return security_scan_service.redact_text(req.text)


@app.post("/security/scan-structured")
def scan_structured_output(req: SecurityScanStructuredRequest):
    return security_scan_service.scan_structured_output(req.data)


@app.post("/trust/annotate")
def annotate_trust_item(req: TrustAnnotationRequest):
    return trust_service.annotate_item(
        item=req.item,
        source_type=req.source_type
    )


@app.post("/autonomy-runs")
def create_autonomy_run(req: AutonomyRunCreateRequest):
    if not planning_service.plan_exists(req.plan_id):
        raise HTTPException(status_code=404, detail="Linked plan not found.")

    if req.reasoning_state_id is not None and not reasoning_service.reasoning_state_exists(req.reasoning_state_id):
        raise HTTPException(status_code=404, detail="Linked reasoning state not found.")

    if req.status not in VALID_AUTONOMY_RUN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid autonomy run status.")

    if req.max_steps is not None and req.max_steps < 1:
        raise HTTPException(status_code=400, detail="max_steps must be >= 1.")

    if req.max_tool_calls is not None and req.max_tool_calls < 0:
        raise HTTPException(status_code=400, detail="max_tool_calls must be >= 0.")

    run_id = autonomy_service.create_autonomy_run(
        plan_id=req.plan_id,
        reasoning_state_id=req.reasoning_state_id,
        status=req.status or "draft",
        max_steps=req.max_steps if req.max_steps is not None else 10,
        steps_executed=req.steps_executed if req.steps_executed is not None else 0,
        max_tool_calls=req.max_tool_calls if req.max_tool_calls is not None else 20,
        tool_calls_used=req.tool_calls_used if req.tool_calls_used is not None else 0,
        stop_reason=req.stop_reason or ""
    )

    return {
        "message": "Autonomy run created successfully.",
        "autonomy_run": autonomy_service.get_autonomy_run_by_id(run_id)
    }


@app.get("/autonomy-runs")
def list_autonomy_runs(
    status: str | None = None,
    plan_id: int | None = None,
    reasoning_state_id: int | None = None,
    limit: int = 100
):
    if status is not None and status not in VALID_AUTONOMY_RUN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid autonomy run status.")

    if plan_id is not None and not planning_service.plan_exists(plan_id):
        raise HTTPException(status_code=404, detail="Linked plan not found.")

    if reasoning_state_id is not None and not reasoning_service.reasoning_state_exists(reasoning_state_id):
        raise HTTPException(status_code=404, detail="Linked reasoning state not found.")

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    return {
        "autonomy_runs": autonomy_service.list_autonomy_runs(
            status=status,
            plan_id=plan_id,
            reasoning_state_id=reasoning_state_id,
            limit=limit
        )
    }


@app.get("/autonomy-runs/{run_id}")
def get_autonomy_run(run_id: int):
    run = autonomy_service.get_autonomy_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return run


@app.patch("/autonomy-runs/{run_id}")
def update_autonomy_run(run_id: int, req: AutonomyRunUpdateRequest):
    if req.status is not None and req.status not in VALID_AUTONOMY_RUN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid autonomy run status.")

    if req.max_steps is not None and req.max_steps < 1:
        raise HTTPException(status_code=400, detail="max_steps must be >= 1.")

    if req.max_tool_calls is not None and req.max_tool_calls < 0:
        raise HTTPException(status_code=400, detail="max_tool_calls must be >= 0.")

    updated = autonomy_service.update_autonomy_run(
        run_id=run_id,
        status=req.status,
        max_steps=req.max_steps,
        steps_executed=req.steps_executed,
        max_tool_calls=req.max_tool_calls,
        tool_calls_used=req.tool_calls_used,
        stop_reason=req.stop_reason
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return {
        "message": "Autonomy run updated successfully.",
        "autonomy_run": updated
    }


@app.get("/autonomy-runs/{run_id}/readiness")
def get_autonomy_run_readiness(run_id: int):
    readiness = autonomy_service.evaluate_run_readiness(run_id)
    if not readiness:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return readiness


@app.get("/autonomy-runs/{run_id}/environment")
def get_autonomy_run_environment(run_id: int):
    snapshot = autonomy_service.get_environment_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return snapshot


@app.get("/autonomy-runs/{run_id}/next-action")
def get_autonomy_next_action(run_id: int):
    decision = autonomy_service.select_next_autonomy_action(run_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return decision


@app.post("/autonomy-runs/{run_id}/run-next-step")
def run_next_autonomy_step(run_id: int):
    result = autonomy_service.run_next_step(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return result


@app.post("/autonomy-runs/{run_id}/pause")
def pause_autonomy_run(run_id: int, reason: str = ""):
    run = autonomy_service.pause_run(run_id, reason=reason)
    if not run:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return {
        "message": "Autonomy run paused successfully.",
        "autonomy_run": run
    }


@app.post("/autonomy-runs/{run_id}/resume")
def resume_autonomy_run(run_id: int):
    try:
        run = autonomy_service.resume_run(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not run:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return {
        "message": "Autonomy run resumed successfully.",
        "autonomy_run": run
    }


@app.post("/autonomy-runs/{run_id}/complete")
def complete_autonomy_run(run_id: int, reason: str = ""):
    run = autonomy_service.complete_run(run_id, reason=reason)
    if not run:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return {
        "message": "Autonomy run completed successfully.",
        "autonomy_run": run
    }


@app.post("/autonomy-runs/{run_id}/handoff")
def handoff_autonomy_run(run_id: int, reason: str = ""):
    run = autonomy_service.handoff_run(run_id, reason=reason)
    if not run:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return {
        "message": "Autonomy run handed off successfully.",
        "autonomy_run": run,
        "handoff_summary": autonomy_service.build_handoff_summary(run_id)
    }


@app.get("/autonomy-runs/{run_id}/handoff-summary")
def get_autonomy_handoff_summary(run_id: int):
    summary = autonomy_service.build_handoff_summary(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Autonomy run not found.")

    return summary
