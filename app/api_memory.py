from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import re
import os

from app.services.memory_service import MemoryService
from app.services.fact_extractor import FactExtractor
from app.services.llm_service import LLMService
from app.services.consolidation_service import ConsolidationService
from app.services.retrieval_orchestrator import RetrievalOrchestrator
from app.services.prompt_builder import PromptBuilder
from app.services.routing_service import RoutingService
from app.services.continuity_service import ContinuityService
from app.services.continuity_extractor import ContinuityExtractor
from app.services.semantic_memory_service import SemanticMemoryService
from app.services.execution_orchestrator import ExecutionOrchestrator
from app.db.database import get_connection
from app.config import settings

router = APIRouter(prefix="/memory", tags=["memory"])

memory_service = MemoryService()
fact_extractor = FactExtractor()
llm_service = LLMService()
consolidation_service = ConsolidationService()
retrieval_orchestrator = RetrievalOrchestrator()
prompt_builder = PromptBuilder()
routing_service = RoutingService()
continuity_service = ContinuityService()
continuity_extractor = ContinuityExtractor()
semantic_memory_service = SemanticMemoryService()
execution_orchestrator = ExecutionOrchestrator()


@router.get("/facts")
def get_facts(category: Optional[str] = None, limit: int = Query(50, le=200)):
    facts = memory_service.get_active_facts()
    if category:
        facts = [f for f in facts if f.get("category") == category]
    return {"facts": facts[:limit], "total": len(facts)}


@router.get("/facts/{fact_id}")
def get_fact(fact_id: int):
    fact = memory_service.get_fact_by_id(fact_id)
    if not fact:
        raise HTTPException(404, "Fact not found")
    return fact


@router.get("/extract")
def extract_facts(text: str):
    facts = fact_extractor.extract(text)
    return {"extracted": facts, "count": len(facts)}


@router.get("/store")
def store_facts(text: str, conversation_id: int = 0):
    if not conversation_id:
        conversation_id = memory_service.create_conversation("API")
    msg_id = memory_service.save_message(conversation_id, "user", text)
    stored = memory_service.extract_and_store_facts(conversation_id, text, msg_id)
    return {"stored": stored, "count": len(stored)}


@router.post("/consolidate")
def consolidate():
    removed = consolidation_service.consolidate_facts()
    return {"facts_removed": removed}


@router.get("/stats")
def memory_stats():
    return consolidation_service.get_memory_stats()


@router.post("/chat")
def chat_with_memory(message: str):
    conversation_id = memory_service.create_conversation("API Chat")
    user_message_id = memory_service.save_message(conversation_id, "user", message)

    # Extract facts and continuity from user message
    memory_service.extract_and_store_facts(conversation_id, message, user_message_id)
    extracted_continuity = continuity_extractor.extract(message)
    continuity_service.auto_store_extracted_items(
        extracted=extracted_continuity,
        conversation_id=conversation_id,
        project_id=None,
    )

    # Check for execution intent
    intent = execution_orchestrator.detect_intent(message, conversation_id)

    if intent == "execute":
        result = execution_orchestrator.handle_execution(conversation_id)
    elif intent == "continue":
        result = execution_orchestrator.handle_continue(conversation_id)
    elif intent == "done":
        result = execution_orchestrator.handle_done(conversation_id)
    elif intent == "verify":
        result = execution_orchestrator.handle_verify(conversation_id)
    elif intent == "pause":
        result = execution_orchestrator.handle_pause(conversation_id)
    elif intent == "abort":
        result = execution_orchestrator.handle_abort(conversation_id)
    elif intent == "status":
        result = execution_orchestrator.handle_status(conversation_id)
    else:
        result = None

    # If execution handled the intent, return directly
    if result and result.get("type") != "no_execution":
        ai_response = result["response"]
        memory_service.save_message(conversation_id, "assistant", ai_response)
        return {
            "response": ai_response,
            "model": "execution-orchestrator",
            "execution_event": result["type"],
        }

    # Normal chat flow — build full context
    exec_state = execution_orchestrator.get_execution_context(conversation_id)

    if exec_state:
        # In execution mode but received a regular message — use locked prompt
        # but still include user message and recent history
        built_system_prompt = execution_orchestrator.build_execution_system_prompt("", exec_state)
        model = routing_service.choose_model(message)
        messages = [{"role": "system", "content": built_system_prompt}]
        # Include recent conversation history
        recent = memory_service.get_recent_messages(conversation_id, limit=6)
        for msg in recent:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    else:
        context_package = retrieval_orchestrator.build_context_package(
            query=message,
            conversation_id=conversation_id,
            retrieval_mode="balanced",
        )
        built_system_prompt = prompt_builder.build_system_prompt(
            profile_summary=context_package.get("profile_summary"),
            facts=context_package.get("facts"),
            retrieved_contexts=context_package.get("retrieved_contexts"),
            retrieved_memories=context_package.get("retrieved_memories"),
            continuity=context_package.get("continuity"),
            reflections=context_package.get("reflections"),
            temporal=context_package.get("temporal"),
            proactive=context_package.get("proactive"),
            reasoning=context_package.get("reasoning"),
            query_type=context_package.get("query_type"),
        )
        recent_messages = context_package.get("recent_messages", [])
        model = routing_service.choose_model(message)
        messages = [{"role": "system", "content": built_system_prompt}]
        for msg in recent_messages:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    result = llm_service.chat(model=model, messages=messages)
    memory_service.save_message(conversation_id, "assistant", result["content"])

    return {
        "response": result["content"],
        "model": result["model"],
        "usage": result.get("usage", {}),
    }


@router.post("/chat/stream")
def chat_with_memory_stream(message: str):
    # Create conversation and save user message
    conversation_id = memory_service.create_conversation("Chat Session")
    user_message_id = memory_service.save_message(conversation_id, "user", message)

    # Extract facts and continuity from user message
    memory_service.extract_and_store_facts(conversation_id, message, user_message_id)
    extracted_continuity = continuity_extractor.extract(message)
    continuity_service.auto_store_extracted_items(
        extracted=extracted_continuity,
        conversation_id=conversation_id,
        project_id=None,
    )

    # Store semantic memory
    semantic_memory_service.store_message_memory(
        conversation_id=conversation_id,
        message_id=user_message_id,
        role="user",
        content=message,
    )

    # Check for execution intent
    intent = execution_orchestrator.detect_intent(message, conversation_id)

    if intent in ("execute", "continue", "done", "verify", "pause", "abort", "status"):
        if intent == "execute":
            result = execution_orchestrator.handle_execution(conversation_id)
        elif intent == "continue":
            result = execution_orchestrator.handle_continue(conversation_id)
        elif intent == "done":
            result = execution_orchestrator.handle_done(conversation_id)
        elif intent == "verify":
            result = execution_orchestrator.handle_verify(conversation_id)
        elif intent == "pause":
            result = execution_orchestrator.handle_pause(conversation_id)
        elif intent == "abort":
            result = execution_orchestrator.handle_abort(conversation_id)
        else:
            result = execution_orchestrator.handle_status(conversation_id)

        if result:
            ai_response = result["response"]
            memory_service.save_message(conversation_id, "assistant", ai_response)

            # Build intelligence metadata for the frontend
            intel_meta = {
                "execution_event": result["type"],
            }
            # Include step intelligence if available
            if result.get("step_id"):
                step = execution_orchestrator.planning_service.get_plan_step_by_id(result["step_id"])
                plan = execution_orchestrator.planning_service.get_plan_by_id(result.get("plan_id", 0))
                if step and plan:
                    confidence, risk = execution_orchestrator._assess_step(step, plan)
                    prediction = execution_orchestrator._generate_prediction(step, plan)
                    known = execution_orchestrator._get_successful_pattern(step)
                    project_insight = execution_orchestrator._get_project_insight(plan)
                    progress = execution_orchestrator.planning_service.get_plan_progress_summary(result["plan_id"])

                    learning = execution_orchestrator._get_step_learning_patterns(step)
                    adapted = execution_orchestrator._get_adapted_strategy(step)

                    intel_meta["intelligence"] = {
                        "step_title": step["title"],
                        "step_description": step.get("description", ""),
                        "step_order": step.get("step_order", 0),
                        "step_id": step["id"],
                        "plan_id": plan["id"],
                        "confidence": confidence,
                        "risk": risk,
                        "prediction": prediction,
                        "known_solution": known["solution_summary"] if known else None,
                        "known_count": known["success_count"] if known else 0,
                        "project_insight": project_insight,
                        "plan_title": plan["title"],
                        "progress": progress["counts"] if progress else None,
                        "sample_size": learning["sample_size"] if learning else 0,
                        "next_action": adapted or step.get("description", "Work through this step carefully."),
                    }

            def execution_generator():
                # Stream the execution response token by token
                for char in ai_response:
                    yield f"data: {json.dumps({'token': char})}\n\n"
                # Send intelligence metadata at the end
                yield f"data: {json.dumps(intel_meta)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(execution_generator(), media_type="text/event-stream")

    # Normal chat flow
    exec_state = execution_orchestrator.get_execution_context(conversation_id)

    if exec_state:
        # In execution mode — use locked prompt with intelligence,
        # but include user message and recent history
        built_system_prompt = execution_orchestrator.build_execution_system_prompt("", exec_state)
        model = routing_service.choose_model(message)
        messages = [{"role": "system", "content": built_system_prompt}]
        recent = memory_service.get_recent_messages(conversation_id, limit=6)
        for msg in recent:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    else:
        # Build full context using the orchestrator
        context_package = retrieval_orchestrator.build_context_package(
            query=message,
            conversation_id=conversation_id,
            retrieval_mode="balanced",
        )

        built_system_prompt = prompt_builder.build_system_prompt(
            profile_summary=context_package.get("profile_summary"),
            facts=context_package.get("facts"),
            retrieved_contexts=context_package.get("retrieved_contexts"),
            retrieved_memories=context_package.get("retrieved_memories"),
            continuity=context_package.get("continuity"),
            reflections=context_package.get("reflections"),
            temporal=context_package.get("temporal"),
            proactive=context_package.get("proactive"),
            reasoning=context_package.get("reasoning"),
            query_type=context_package.get("query_type"),
        )

        recent_messages = context_package.get("recent_messages", [])
        model = routing_service.choose_model(message)

        messages = [{"role": "system", "content": built_system_prompt}]
        for msg in recent_messages:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    def event_generator():
        full_content = ""
        try:
            for token in llm_service.stream_chat(model, messages):
                full_content += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Save assistant message after streaming completes
        try:
            memory_service.save_message(conversation_id, "assistant", full_content)

            # Store semantic memory for the assistant response
            semantic_memory_service.store_message_memory(
                conversation_id=conversation_id,
                message_id=0,
                role="assistant",
                content=full_content,
            )

            # Auto-consolidate
            consolidation_service.check_and_consolidate_conversation(conversation_id)
        except Exception:
            pass

        # Check for code blocks and create files
        created_files = _create_files_from_code_blocks(full_content)
        if created_files:
            yield f"data: {json.dumps({'files_created': created_files})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _create_files_from_code_blocks(content: str) -> list[str]:
    """Parse code blocks with filename headers and save to data/projects/."""
    projects_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "projects")
    os.makedirs(projects_dir, exist_ok=True)

    created = []
    # Match code blocks with optional filename: ```lang filename=path or ```lang path
    pattern = r"```(\w*)\s*(?:filename[:=]\s*([^\n]+)|path[:=]\s*([^\n]+))?\s*\n(.*?)```"
    for match in re.finditer(pattern, content, re.DOTALL):
        _lang, filename1, filename2, code = match.groups()
        filename = (filename1 or filename2 or "").strip()
        if not filename:
            continue

        # Sanitize path - prevent directory traversal
        safe_filename = os.path.basename(filename)
        filepath = os.path.join(projects_dir, safe_filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            created.append(safe_filename)
        except OSError:
            continue

    return created


@router.post("/files/create")
def create_file(filename: str, content: str):
    """Manually create a file in data/projects/."""
    projects_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "projects")
    os.makedirs(projects_dir, exist_ok=True)

    safe_filename = os.path.basename(filename)
    filepath = os.path.join(projects_dir, safe_filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise HTTPException(500, f"Failed to create file: {e}")

    return {"created": safe_filename, "path": filepath}


@router.get("/files")
def list_files():
    """List files in data/projects/."""
    projects_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "projects")
    if not os.path.isdir(projects_dir):
        return {"files": []}

    files = []
    for name in sorted(os.listdir(projects_dir)):
        path = os.path.join(projects_dir, name)
        if os.path.isfile(path):
            files.append({
                "name": name,
                "size": os.path.getsize(path),
            })
    return {"files": files}


@router.post("/feedback")
def submit_feedback(plan_id: int, step_id: int, outcome: str, reason: str = ""):
    """Submit user feedback on step outcome.

    outcome: 'success', 'partial', 'failure'
    """
    if outcome not in ("success", "partial", "failure"):
        raise HTTPException(400, "outcome must be 'success', 'partial', or 'failure'")

    # Log feedback as an execution event
    event_type = "complete" if outcome == "success" else ("retry" if outcome == "partial" else "fail")
    message = f"User feedback: {outcome}"
    if reason:
        message += f" — {reason}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO execution_events (plan_id, step_id, event_type, message, confidence, risk_level)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (plan_id, step_id, event_type, message,
          1.0 if outcome == "success" else (0.5 if outcome == "partial" else 0.1),
          "low" if outcome == "success" else ("medium" if outcome == "partial" else "high")))
    conn.commit()
    conn.close()

    # If successful, record pattern for reuse
    if outcome == "success":
        step = execution_orchestrator.planning_service.get_plan_step_by_id(step_id)
        if step:
            execution_orchestrator._record_successful_pattern(
                step,
                solution_summary=f"User confirmed: {step['title']} completed successfully.",
                strategy=reason[:200] if reason else "",
            )

    return {"status": "recorded", "outcome": outcome}


@router.get("/learning")
def learning_insights():
    """Aggregate learning analytics for the Learning Insights panel."""
    conn = get_connection()
    cur = conn.cursor()

    # Overall stats
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN event_type = 'complete' THEN 1 ELSE 0 END) as completions,
            SUM(CASE WHEN event_type = 'fail' THEN 1 ELSE 0 END) as failures,
            SUM(CASE WHEN event_type = 'retry' THEN 1 ELSE 0 END) as retries,
            SUM(CASE WHEN event_type = 'stuck' THEN 1 ELSE 0 END) as stuck,
            SUM(CASE WHEN event_type = 'verify' THEN 1 ELSE 0 END) as verifications
        FROM execution_events
    """)
    overall = cur.fetchone() or {}

    total = overall.get("total", 0) or 0
    completions = overall.get("completions", 0) or 0
    failures = overall.get("failures", 0) or 0

    # Success rate trend — compare last 7 days vs prior 7 days
    cur.execute("""
        SELECT
            SUM(CASE WHEN event_type = 'complete' THEN 1 ELSE 0 END) as recent_completions,
            COUNT(*) as recent_total
        FROM execution_events
        WHERE created_at >= datetime('now', '-7 days')
    """)
    recent = cur.fetchone() or {}
    recent_total = recent.get("recent_total", 0) or 0
    recent_completions = recent.get("recent_completions", 0) or 0

    cur.execute("""
        SELECT
            SUM(CASE WHEN event_type = 'complete' THEN 1 ELSE 0 END) as prior_completions,
            COUNT(*) as prior_total
        FROM execution_events
        WHERE created_at >= datetime('now', '-14 days')
          AND created_at < datetime('now', '-7 days')
    """)
    prior = cur.fetchone() or {}
    prior_total = prior.get("prior_total", 0) or 0
    prior_completions = prior.get("prior_completions", 0) or 0

    recent_rate = round(recent_completions / max(recent_total, 1) * 100)
    prior_rate = round(prior_completions / max(prior_total, 1) * 100)

    # Solutions learned this week
    cur.execute("""
        SELECT COUNT(*) as count FROM successful_patterns
        WHERE created_at >= datetime('now', '-7 days')
    """)
    new_solutions_row = cur.fetchone() or {}
    new_solutions = new_solutions_row.get("count", 0) or 0

    # Total learned patterns
    cur.execute("SELECT COUNT(*) as count FROM successful_patterns")
    total_patterns_row = cur.fetchone() or {}
    total_patterns = total_patterns_row.get("count", 0) or 0

    # Top learned fix
    cur.execute("""
        SELECT step_type, solution_summary, success_count
        FROM successful_patterns
        ORDER BY success_count DESC
        LIMIT 1
    """)
    top_fix = cur.fetchone()

    # Risk distribution
    cur.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM execution_events
        WHERE risk_level IS NOT NULL
        GROUP BY risk_level
    """)
    risk_dist = {row["risk_level"]: row["count"] for row in cur.fetchall()}

    # High-risk failure rate
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN event_type = 'fail' THEN 1 ELSE 0 END) as failures
        FROM execution_events
        WHERE risk_level = 'high'
    """)
    high_risk = cur.fetchone() or {}
    high_risk_total = high_risk.get("total", 0) or 0
    high_risk_failures = high_risk.get("failures", 0) or 0
    high_risk_fail_rate = round(high_risk_failures / max(high_risk_total, 1) * 100)

    # Average confidence
    cur.execute("""
        SELECT AVG(confidence) as avg_conf FROM execution_events
        WHERE confidence IS NOT NULL
    """)
    avg_conf_row = cur.fetchone() or {}
    avg_confidence = round((avg_conf_row.get("avg_conf", 0) or 0) * 100)

    # Most improved step type
    cur.execute("""
        SELECT step_type, success_count
        FROM successful_patterns
        ORDER BY success_count DESC
        LIMIT 1
    """)
    most_improved = cur.fetchone()

    # User impact — count feedback given this week
    cur.execute("""
        SELECT
            COUNT(*) as total_feedback,
            SUM(CASE WHEN message LIKE '%success%' THEN 1 ELSE 0 END) as positive_feedback
        FROM execution_events
        WHERE message LIKE 'User feedback:%'
          AND created_at >= datetime('now', '-7 days')
    """)
    feedback_row = cur.fetchone() or {}
    total_feedback = feedback_row.get("total_feedback", 0) or 0
    positive_feedback = feedback_row.get("positive_feedback", 0) or 0

    # Estimate user impact: feedback contributed to pattern learning
    impact_pct = round(positive_feedback / max(total_feedback, 1) * 3) if total_feedback > 0 else 0

    # Lifetime feedback stats for milestones
    cur.execute("""
        SELECT
            COUNT(*) as lifetime_feedback,
            SUM(CASE WHEN message LIKE '%success%' THEN 1 ELSE 0 END) as lifetime_positive
        FROM execution_events
        WHERE message LIKE 'User feedback:%'
    """)
    lifetime_row = cur.fetchone() or {}
    lifetime_feedback = lifetime_row.get("lifetime_feedback", 0) or 0
    lifetime_positive = lifetime_row.get("lifetime_positive", 0) or 0

    # Milestone detection
    milestone = None
    MILESTONES = [
        (1, "first_feedback", "First feedback given!", "You've started helping the system learn."),
        (5, "five_feedbacks", "5 feedbacks given!", "You're building a learning foundation."),
        (10, "ten_feedbacks", "10 feedbacks given!", "Your feedback helped improve success rate significantly."),
        (25, "twenty_five", "25 feedbacks!", "You've contributed to multiple successful fixes."),
        (50, "fifty", "50 feedbacks — dedicated learner!", "The system is visibly smarter because of you."),
    ]
    for threshold, key, title, desc in MILESTONES:
        if lifetime_feedback == threshold:
            milestone = {"key": key, "title": title, "description": desc, "count": lifetime_feedback}
            break

    # Next milestone
    next_milestone = None
    for threshold, key, title, desc in MILESTONES:
        if lifetime_feedback < threshold:
            next_milestone = {
                "target": threshold,
                "title": title,
                "current": lifetime_feedback,
                "pct": round(lifetime_feedback / threshold * 100),
            }
            break

    conn.close()

    return {
        "total_events": total,
        "success_rate": round(completions / max(total, 1) * 100),
        "success_rate_trend": {
            "current": recent_rate,
            "prior": prior_rate,
            "direction": "up" if recent_rate > prior_rate else ("down" if recent_rate < prior_rate else "flat"),
        },
        "total_patterns": total_patterns,
        "new_solutions_week": new_solutions,
        "top_fix": {
            "type": top_fix["step_type"] if top_fix else None,
            "summary": top_fix["solution_summary"] if top_fix else None,
            "count": top_fix["success_count"] if top_fix else 0,
        } if top_fix else None,
        "high_risk_fail_rate": high_risk_fail_rate,
        "average_confidence": avg_confidence,
        "most_improved": most_improved["step_type"] if most_improved else None,
        "risk_distribution": risk_dist,
        "user_impact": {
            "feedback_count": total_feedback,
            "positive_feedback": positive_feedback,
            "impact_pct": impact_pct,
            "lifetime_feedback": lifetime_feedback,
            "lifetime_positive": lifetime_positive,
            "milestone": milestone,
            "next_milestone": next_milestone,
        },
    }
