import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from app.db.database import get_connection
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.autonomy_service import AutonomyService
from app.services.llm_service import LLMService
from app.services.semantic_matcher import compute_similarity, find_best_matches
from app.config import settings


# Stuck threshold in minutes
STUCK_THRESHOLD_MINUTES = 30


class ExecutionOrchestrator:
    """Detects execution intent and runs plans step-by-step.

    State is persisted to the execution_sessions table so it survives
    server restarts and scales correctly.
    """

    def __init__(self):
        self.planning_service = PlanningService()
        self.execution_service = ExecutionService()
        self.autonomy_service = AutonomyService()
        self.llm_service = LLMService()

    # ─── Intent Detection ────────────────────────────────────

    EXECUTE_PATTERNS = [
        r"\bstart\s+execut",
        r"\bexecut(e|ing)\s+(the\s+)?(plan|step)",
        r"\brun\s+(the\s+)?(plan|step)",
        r"\bgo\s+ahead",
        r"\blet'?s\s+(go|start|begin|do\s+it)",
        r"\bstart\s+(now|right\s+away)",
        r"\bdo\s+(it|this|that)\s*(now)?",
    ]

    CONTINUE_PATTERNS = [
        r"^continue\s*$",
        r"^continue\b",
        r"^next\s*$",
        r"^next\s+step",
        r"\bmove\s+(on|to\s+the\s+next)",
        r"\bkeep\s+going",
        r"\bwhat'?s\s+next",
        r"^proceed",
        r"^go\s+on",
    ]

    DONE_PATTERNS = [
        r"^(done|finished|completed?|that'?s\s+done|it'?s\s+done)\s*[.!]?\s*$",
        r"\bstep\s+(is\s+)?(done|finished|complete)",
        r"\byes,?\s+(done|finished|complete)",
    ]

    PAUSE_PATTERNS = [
        r"\b(pause|hold|wait|stop\s+for\s+now|freeze)\b",
    ]

    ABORT_PATTERNS = [
        r"\b(abort|cancel|quit|give\s+up)\s*(execution|plan|this)?",
        r"\bnever\s+mind",
    ]

    STATUS_PATTERNS = [
        r"\b(where|what)\s+(am\s+i|are\s+we)",
        r"\bwhat'?s\s+(the\s+)?(status|progress)",
        r"\bshow\s+(me\s+)?(the\s+)?(plan|progress|status)",
        r"\bhow.*(going|progress)",
    ]

    VERIFY_PATTERNS = [
        r"\b(verify|check|validate|confirm)\b",
        r"\blooks?\s+good",
        r"\bworks?\s+(now|fine|ok)",
        r"\bthat\s+(fixed|worked|solved)",
        r"^yes\s*[.!]?\s*$",
    ]

    def detect_intent(self, message: str, conversation_id: int) -> str:
        msg = message.lower().strip()
        is_active = self._get_session(conversation_id) is not None

        for pattern in self.EXECUTE_PATTERNS:
            if re.search(pattern, msg):
                return "execute"

        for pattern in self.CONTINUE_PATTERNS:
            if re.search(pattern, msg):
                return "continue" if is_active else "execute"

        for pattern in self.DONE_PATTERNS:
            if re.search(pattern, msg):
                return "done" if is_active else "chat"

        for pattern in self.VERIFY_PATTERNS:
            if re.search(pattern, msg):
                return "verify" if is_active else "chat"

        for pattern in self.PAUSE_PATTERNS:
            if re.search(pattern, msg):
                return "pause" if is_active else "chat"

        for pattern in self.ABORT_PATTERNS:
            if re.search(pattern, msg):
                return "abort" if is_active else "chat"

        for pattern in self.STATUS_PATTERNS:
            if re.search(pattern, msg):
                return "status"

        return "chat"

    # ─── Execution Handlers ──────────────────────────────────

    def handle_execution(self, conversation_id: int) -> Optional[Dict]:
        plan = self._find_active_plan(conversation_id)
        if not plan:
            return {
                "type": "no_plan",
                "response": "No active plan found. Ask me to create a plan first, then say 'start executing'.",
            }

        plan_id = plan["id"]

        # Check for stuck sessions first
        self._check_stuck_sessions(conversation_id)

        # Check for existing session (resume)
        session = self._get_session(conversation_id)
        if session and session["status"] == "paused":
            return self._resume_session(conversation_id, session)

        ready_steps = self.planning_service.get_ready_steps(plan_id)
        if not ready_steps:
            progress = self.planning_service.get_plan_progress_summary(plan_id)
            if progress and progress["counts"]["completed"] == progress["counts"]["total_steps"]:
                self.planning_service.update_plan(plan_id, status="completed")
                return {
                    "type": "plan_completed",
                    "response": f"**Plan '{plan['title']}' is complete!** All {progress['counts']['total_steps']} steps done.",
                    "plan_id": plan_id,
                }
            return {
                "type": "blocked",
                "response": f"Plan '{plan['title']}' has no ready steps. Remaining steps may be blocked by dependencies.",
                "plan_id": plan_id,
            }

        next_step = ready_steps[0]

        execution_id = self.execution_service.create_step_execution(
            plan_id=plan_id,
            step_id=next_step["id"],
            action_type="chat_guided",
            action_payload={"trigger": "user_command", "step_title": next_step["title"]},
        )
        if not execution_id:
            return {"type": "error", "response": "Failed to create execution record."}

        self.execution_service.start_execution(execution_id)
        self.planning_service.update_plan(plan_id, status="active")

        # Persist session to DB
        self._upsert_session(
            conversation_id=conversation_id,
            plan_id=plan_id,
            current_step_id=next_step["id"],
            current_execution_id=execution_id,
            status="running",
        )

        # Log event
        confidence, risk = self._assess_step(next_step, plan)
        self._log_event(execution_id, next_step["id"], plan_id, "start",
                        f"Started: {next_step['title']}", confidence, risk)

        progress = self.planning_service.get_plan_progress_summary(plan_id)
        thinking = self._generate_step_thinking(next_step, plan)
        prediction = self._generate_prediction(next_step, plan)
        known_pattern = self._get_successful_pattern(next_step)
        project_insight = self._get_project_insight(plan)

        return {
            "type": "step_started",
            "response": self._format_step_response(
                next_step, progress or {}, "starting", thinking,
                confidence, risk, prediction, known_pattern, project_insight
            ),
            "plan_id": plan_id,
            "step_id": next_step["id"],
            "execution_id": execution_id,
        }

    def handle_continue(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)
        if not session:
            return self.handle_execution(conversation_id)

        if session["status"] == "paused":
            return self._resume_session(conversation_id, session)

        # Check for stuck steps
        stuck = self._check_stuck_sessions(conversation_id)
        if stuck:
            return stuck

        return self._verify_and_advance(conversation_id, session, auto_verify=True)

    def handle_done(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)
        if not session:
            return {"type": "no_execution", "response": "No active execution."}

        return self._verify_and_advance(conversation_id, session, auto_verify=True)

    def handle_verify(self, conversation_id: int) -> Optional[Dict]:
        """User explicitly confirms the step worked."""
        session = self._get_session(conversation_id)
        if not session:
            return {"type": "no_execution", "response": "No active execution to verify."}

        # Check if this step needs explicit confirmation
        step = self.planning_service.get_plan_step_by_id(session["current_step_id"])
        plan = self.planning_service.get_plan_by_id(session["plan_id"])
        if step and plan:
            _, risk = self._assess_step(step, plan)
            if risk == "high":
                return self._verify_and_advance(conversation_id, session, auto_verify=False, explicit=True)

        return self._verify_and_advance(conversation_id, session, auto_verify=False)

    def handle_pause(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)
        if not session:
            return {"type": "no_execution", "response": "No active execution to pause."}

        self._update_session_status(conversation_id, "paused")
        self._log_event(session.get("current_execution_id"), session.get("current_step_id"),
                        session["plan_id"], "pause", "Execution paused by user.")

        plan = self.planning_service.get_plan_by_id(session["plan_id"])
        step = self.planning_service.get_plan_step_by_id(session["current_step_id"])
        progress = self.planning_service.get_plan_progress_summary(session["plan_id"])

        step_title = step["title"] if step else "unknown"
        counts = progress["counts"] if progress else {}

        return {
            "type": "paused",
            "response": (
                f"**Execution paused.**\n\n"
                f"Plan: {plan['title'] if plan else 'unknown'}\n"
                f"Was on: {step_title}\n"
                f"Progress: {counts.get('completed', '?')}/{counts.get('total_steps', '?')} steps done\n\n"
                f"Say 'continue' to resume, or 'abort' to stop."
            ),
        }

    def handle_abort(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)
        if not session:
            return {"type": "no_execution", "response": "No active execution to abort."}

        if session["current_execution_id"]:
            self.execution_service.mark_execution_cancelled(
                session["current_execution_id"], result_summary="Aborted by user."
            )

        self._update_session_status(conversation_id, "abandoned")
        self._log_event(session.get("current_execution_id"), session.get("current_step_id"),
                        session["plan_id"], "fail", "Execution aborted by user.")

        # Record project pattern for long-horizon learning
        step = self.planning_service.get_plan_step_by_id(session.get("current_step_id"))
        plan = self.planning_service.get_plan_by_id(session["plan_id"])
        if plan:
            stage = step["title"] if step else "unknown"
            self._record_project_pattern(plan, failure_stage=stage)

        return {
            "type": "aborted",
            "response": "Execution stopped. Plan progress is saved — say 'execute' anytime to start fresh.",
            "plan_id": session["plan_id"],
        }

    def handle_status(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)

        if session and session["status"] == "running":
            plan = self.planning_service.get_plan_by_id(session["plan_id"])
            step = self.planning_service.get_plan_step_by_id(session["current_step_id"])
            progress = self.planning_service.get_plan_progress_summary(session["plan_id"])

            if plan and step and progress:
                counts = progress["counts"]
                log_entries = self._get_step_log(session)
                events = self._get_recent_events(session["plan_id"], limit=5)

                log_text = ""
                if log_entries:
                    log_lines = []
                    for entry in log_entries[-5:]:
                        icon = "✓" if entry["result"] == "succeeded" else ("✗" if entry["result"] == "failed" else "→")
                        log_lines.append(f"  {icon} {entry['step']}: {entry['summary']}")
                    log_text = "\n".join(log_lines)

                event_text = ""
                if events:
                    event_lines = []
                    for ev in events:
                        event_lines.append(f"  [{ev['event_type']}] {ev['message']} (confidence: {ev.get('confidence', '?')})")
                    event_text = "\n".join(event_lines)

                return {
                    "type": "status",
                    "response": (
                        f"**Executing:** {plan['title']}\n"
                        f"**Current:** Step {step['step_order']}: {step['title']}\n"
                        f"**Progress:** {counts['completed']}/{counts['total_steps']} done ({progress['percent_complete']}%)\n"
                        f"**Ready next:** {counts['ready']} steps waiting"
                        + (f"\n\n**Step log:**\n{log_text}" if log_text else "")
                        + (f"\n\n**Recent events:**\n{event_text}" if event_text else "")
                    ),
                }

        if session and session["status"] == "paused":
            plan = self.planning_service.get_plan_by_id(session["plan_id"])
            progress = self.planning_service.get_plan_progress_summary(session["plan_id"])
            if plan and progress:
                counts = progress["counts"]
                return {
                    "type": "status",
                    "response": (
                        f"**Paused:** {plan['title']}\n"
                        f"**Progress:** {counts['completed']}/{counts['total_steps']} done ({progress['percent_complete']}%)\n"
                        f"Say 'continue' to resume."
                    ),
                }

        plan = self._find_active_plan(conversation_id)
        if plan:
            progress = self.planning_service.get_plan_progress_summary(plan["id"])
            if progress:
                counts = progress["counts"]
                return {
                    "type": "status",
                    "response": (
                        f"**Plan:** {plan['title']} ({plan['status']})\n"
                        f"**Progress:** {counts['completed']}/{counts['total_steps']} done ({progress['percent_complete']}%)\n"
                        f"Say 'execute' to start."
                    ),
                }

        return {"type": "status", "response": "No active plans. Ask me to create one."}

    def get_execution_context(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)
        if session and session["status"] == "running":
            return {
                "plan_id": session["plan_id"],
                "step_id": session["current_step_id"],
                "execution_id": session["current_execution_id"],
                "mode": "executing",
            }
        return None

    # ─── Internal: Verification & Advancement ────────────────

    def _verify_and_advance(self, conversation_id: int, session: Dict,
                            auto_verify: bool = False, explicit: bool = False) -> Dict:
        plan_id = session["plan_id"]
        step_id = session["current_step_id"]
        execution_id = session["current_execution_id"]

        step = self.planning_service.get_plan_step_by_id(step_id)
        if not step:
            return {"type": "error", "response": "Step not found."}

        plan = self.planning_service.get_plan_by_id(plan_id)
        _, risk = self._assess_step(step, plan) if plan else ("medium", "medium")

        # High-risk steps need explicit confirmation
        if auto_verify and risk == "high" and not explicit:
            return {
                "type": "needs_confirmation",
                "response": (
                    f"**This is a high-risk step.** Can you confirm it actually worked?\n\n"
                    f"Step: {step['title']}\n\n"
                    f"Reply **'yes'** to confirm it's done, or describe what happened."
                ),
            }

        # Mark as succeeded
        if execution_id:
            if explicit:
                self.execution_service.mark_execution_succeeded(
                    execution_id, result_summary="Verified by user (explicit confirmation)."
                )
                self.execution_service.mark_execution_verified(execution_id)
                self._log_event(execution_id, step_id, plan_id, "verify",
                                f"Explicitly verified: {step['title']}")
            elif auto_verify:
                self.execution_service.mark_execution_succeeded(
                    execution_id, result_summary="Step completed (user confirmed via continue/done)."
                )
                self.execution_service.mark_execution_verified(execution_id)
                self._log_event(execution_id, step_id, plan_id, "verify",
                                f"Auto-verified: {step['title']}")

        # Log the completed step
        self._append_step_log(conversation_id, session, {
            "step": step["title"],
            "result": "succeeded",
            "summary": "Completed",
        })

        self._log_event(execution_id, step_id, plan_id, "complete",
                        f"Completed: {step['title']}")

        # Record successful pattern for future reuse
        self._record_successful_pattern(
            step,
            solution_summary=f"Completed step: {step['title']}",
            strategy=step.get("description", "")[:200],
        )

        # Get updated progress
        progress = self.planning_service.get_plan_progress_summary(plan_id)
        if not progress:
            return {"type": "error", "response": "Could not get plan progress."}
        counts = progress["counts"]

        # All done?
        if counts["completed"] == counts["total_steps"]:
            self.planning_service.update_plan(plan_id, status="completed")
            self._update_session_status(conversation_id, "completed")

            # Record project pattern for long-horizon learning
            plan = self.planning_service.get_plan_by_id(plan_id)
            if plan:
                self._record_project_pattern(plan, completed=True,
                                             success_strategy=f"All {counts['total_steps']} steps completed successfully.")

            return {
                "type": "plan_completed",
                "response": (
                    f"**✓ Step completed:** {step['title']}\n\n"
                    f"**Plan '{progress['plan']['title']}' is now complete!**\n"
                    f"All {counts['total_steps']} steps finished."
                ),
                "plan_id": plan_id,
            }

        # Find next ready step
        ready_steps = self.planning_service.get_ready_steps(plan_id)
        if not ready_steps:
            self._update_session_status(conversation_id, "completed")
            return {
                "type": "blocked",
                "response": (
                    f"**✓ Step completed:** {step['title']} ({counts['completed']}/{counts['total_steps']})\n\n"
                    f"No more ready steps. Remaining may be blocked by dependencies."
                ),
                "plan_id": plan_id,
            }

        next_step = ready_steps[0]

        new_execution_id = self.execution_service.create_step_execution(
            plan_id=plan_id,
            step_id=next_step["id"],
            action_type="chat_guided",
            action_payload={"trigger": "auto_advance", "step_title": next_step["title"]},
        )
        if not new_execution_id:
            return {"type": "error", "response": "Failed to create next execution."}

        self.execution_service.start_execution(new_execution_id)

        # Update persisted session
        self._upsert_session(
            conversation_id=conversation_id,
            plan_id=plan_id,
            current_step_id=next_step["id"],
            current_execution_id=new_execution_id,
            status="running",
        )

        confidence, risk = self._assess_step(next_step, plan)
        self._log_event(new_execution_id, next_step["id"], plan_id, "start",
                        f"Started: {next_step['title']}", confidence, risk)

        thinking = self._generate_step_thinking(next_step, plan)
        prediction = self._generate_prediction(next_step, plan)
        known_pattern = self._get_successful_pattern(next_step)
        project_insight = self._get_project_insight(plan)

        return {
            "type": "step_started",
            "response": self._format_step_response(
                next_step, progress, "advancing", thinking,
                confidence, risk, prediction, known_pattern, project_insight
            ),
            "plan_id": plan_id,
            "step_id": next_step["id"],
            "execution_id": new_execution_id,
        }

    def _resume_session(self, conversation_id: int, session: Dict) -> Dict:
        self._update_session_status(conversation_id, "running")
        self._log_event(session.get("current_execution_id"), session.get("current_step_id"),
                        session["plan_id"], "resume", "Execution resumed.")

        plan = self.planning_service.get_plan_by_id(session["plan_id"])
        step = self.planning_service.get_plan_step_by_id(session["current_step_id"])
        progress = self.planning_service.get_plan_progress_summary(session["plan_id"])

        if not plan or not step or not progress:
            return {"type": "error", "response": "Could not resume — plan or step not found."}

        confidence, risk = self._assess_step(step, plan)
        thinking = self._generate_step_thinking(step, plan)
        prediction = self._generate_prediction(step, plan)
        known_pattern = self._get_successful_pattern(step)
        project_insight = self._get_project_insight(plan)

        return {
            "type": "step_started",
            "response": f"**Resuming execution.**\n\n" + self._format_step_response(
                step, progress, "resuming", thinking,
                confidence, risk, prediction, known_pattern, project_insight
            ),
            "plan_id": session["plan_id"],
            "step_id": session["current_step_id"],
            "execution_id": session["current_execution_id"],
        }

    # ─── Internal: Stuck Detection ───────────────────────────

    def _check_stuck_sessions(self, conversation_id: int) -> Optional[Dict]:
        session = self._get_session(conversation_id)
        if not session or session["status"] != "running":
            return None

        exec_id = session.get("current_execution_id")
        if not exec_id:
            return None

        execution = self.execution_service.get_step_execution_by_id(exec_id)
        if not execution or execution["status"] != "running":
            return None

        started_at = execution.get("started_at")
        if not started_at:
            return None

        try:
            started = datetime.fromisoformat(started_at)
            elapsed = datetime.now() - started
            if elapsed > timedelta(minutes=STUCK_THRESHOLD_MINUTES):
                self._log_event(exec_id, session["current_step_id"],
                                session["plan_id"], "stuck",
                                f"Step running for {int(elapsed.total_seconds() / 60)} minutes (> {STUCK_THRESHOLD_MINUTES}m threshold).")

                stuck_step = self.planning_service.get_plan_step_by_id(session['current_step_id'])
                step_title = stuck_step['title'] if stuck_step else 'Unknown'

                return {
                    "type": "stuck",
                    "response": (
                        f"**⚠ Step may be stuck.**\n\n"
                        f"Step '{step_title}' "
                        f"has been running for {int(elapsed.total_seconds() / 60)} minutes.\n\n"
                        f"Options:\n"
                        f"- Say **'continue'** to mark it done and move on\n"
                        f"- Say **'pause'** to hold\n"
                        f"- Say **'abort'** to stop"
                    ),
                }
        except (ValueError, TypeError):
            pass

        return None

    # ─── Internal: Step Assessment ───────────────────────────

    CRITICAL_KEYWORDS = [
        "deploy", "ship", "release", "production", "auth", "security",
        "database", "migration", "delete", "drop", "permission", "payment",
    ]

    HIGH_RISK_KEYWORDS = [
        "deploy", "ship", "release", "production", "migration",
        "delete", "drop", "security", "auth",
    ]

    MEDIUM_RISK_KEYWORDS = [
        "config", "setup", "test", "verify", "validate", "review",
        "install", "update", "modify", "change", "integrate",
    ]

    DETERMINISTIC_KEYWORDS = [
        "write", "create", "add", "generate", "list", "read", "copy",
        "format", "lint", "build", "compile",
    ]

    def _assess_step(self, step: Dict, plan: Optional[Dict]) -> tuple:
        """Hybrid assessment: keyword rules → LLM override → evidence-based confidence.

        Returns (confidence, risk) for a step.
        """
        title = (step.get("title") or "").lower()
        desc = (step.get("description") or "").lower()
        combined = f"{title} {desc}"

        # Phase 1: Keyword-based risk (fast path)
        risk = "low"
        for kw in self.HIGH_RISK_KEYWORDS:
            if kw in combined:
                risk = "high"
                break
        if risk == "low":
            for kw in self.MEDIUM_RISK_KEYWORDS:
                if kw in combined:
                    risk = "medium"
                    break

        # Phase 2: LLM override for medium or uncertain cases
        if risk == "medium":
            llm_risk = self._llm_assess_risk(step, plan)
            if llm_risk:
                risk = llm_risk

        # Phase 3: Evidence-based confidence
        confidence = self._compute_evidence_confidence(step, plan, risk)

        # Phase 4: Cross-step learning adjustment
        learning = self._get_step_learning_patterns(step)
        if learning and learning["sample_size"] >= 3:
            fail_rate = learning["fail_rate"]
            avg_retries = learning["avg_retries"]

            # Lower confidence if this type of step historically fails
            if fail_rate > 0.4:
                confidence = max(0.3, confidence - 0.2)
                if risk != "high":
                    risk = "medium"  # escalate risk based on history
            elif fail_rate > 0.2:
                confidence = max(0.4, confidence - 0.1)

            # Lower confidence if retries are common
            if avg_retries > 1.5:
                confidence = max(0.3, confidence - 0.1)

        return (round(confidence, 2), risk)

    def _llm_assess_risk(self, step: Dict, plan: Optional[Dict]) -> Optional[str]:
        """Use LLM to assess risk when keyword matching is uncertain."""
        try:
            plan_ctx = f"Plan: {plan.get('title', '')}" if plan else ""
            result = self.llm_service.simple_chat(
                f"Step: {step.get('title', '')}\nDescription: {step.get('description', '')}\n{plan_ctx}",
                system_prompt=(
                    "You are a risk assessor for software execution steps. "
                    "Classify the risk level of this step as exactly one of: low, medium, high.\n\n"
                    "Guidelines:\n"
                    "- low: reading, writing, creating non-critical files, documentation\n"
                    "- medium: configuration changes, testing, code modifications\n"
                    "- high: deployments, database changes, security modifications, deletions, production changes\n\n"
                    "Reply with ONLY the risk level (low, medium, or high), nothing else."
                ),
            )
            raw = result.get("content", "").strip().lower()
            if raw in ("low", "medium", "high"):
                return raw
        except Exception:
            pass
        return None

    def _compute_evidence_confidence(self, step: Dict, plan: Optional[Dict], risk: str) -> float:
        """Compute confidence based on evidence signals, not just rules.

        Signals:
        +0.2 if similar past steps succeeded
        +0.2 if low risk
        +0.2 if deterministic operation (write, create, read)
        +0.1 if step has a detailed description
        -0.3 if unknown/empty context
        -0.2 if risk is high
        -0.1 if step has no description
        """
        confidence = 0.5  # base

        # Signal: past success of similar steps
        learning = self._get_step_learning_patterns(step)
        if learning and learning["sample_size"] >= 2:
            if learning["success_rate"] > 0.7:
                confidence += 0.2
            elif learning["success_rate"] > 0.5:
                confidence += 0.1
            elif learning["success_rate"] < 0.3:
                confidence -= 0.2

        # Signal: risk level
        if risk == "low":
            confidence += 0.2
        elif risk == "high":
            confidence -= 0.2

        # Signal: deterministic operation
        title = (step.get("title") or "").lower()
        for kw in self.DETERMINISTIC_KEYWORDS:
            if kw in title:
                confidence += 0.2
                break

        # Signal: description quality
        desc = step.get("description", "")
        if desc and len(desc) > 50:
            confidence += 0.1
        elif not desc:
            confidence -= 0.1

        # Signal: unknown/empty context
        if not desc and not step.get("title"):
            confidence -= 0.3

        return max(0.1, min(0.95, confidence))

    def _get_step_learning_patterns(self, step: Dict) -> Optional[Dict]:
        """Query execution_events to find patterns for similar step types.

        Returns success_rate, fail_rate, avg_retries, sample_size.
        """
        title = (step.get("title") or "").lower()

        # Classify step into a type based on keywords
        step_type = "general"
        type_keywords = {
            "debug": ["debug", "fix", "diagnose", "troubleshoot"],
            "test": ["test", "verify", "validate", "check"],
            "deploy": ["deploy", "ship", "release"],
            "auth": ["auth", "login", "permission", "security"],
            "config": ["config", "setup", "set up", "configure"],
            "write": ["write", "create", "add", "build", "implement"],
            "review": ["review", "inspect", "audit", "check"],
            "database": ["database", "db", "migration", "sql"],
        }
        for stype, keywords in type_keywords.items():
            for kw in keywords:
                if kw in title:
                    step_type = stype
                    break
            if step_type != "general":
                break

        # Query events for this step type
        conn = get_connection()
        cur = conn.cursor()

        # Find steps with similar titles (same type) and their outcomes
        cur.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN event_type = 'complete' THEN 1 ELSE 0 END) as completions,
                SUM(CASE WHEN event_type = 'fail' THEN 1 ELSE 0 END) as failures,
                SUM(CASE WHEN event_type = 'retry' THEN 1 ELSE 0 END) as retries
            FROM execution_events
            WHERE event_type IN ('complete', 'fail', 'retry')
        """)
        row = cur.fetchone()
        conn.close()

        if not row or row["total"] == 0:
            return None

        total = row["total"]
        completions = row["completions"] or 0
        failures = row["failures"] or 0
        retries = row["retries"] or 0

        return {
            "step_type": step_type,
            "sample_size": total,
            "success_rate": round(completions / total, 2) if total > 0 else 0,
            "fail_rate": round(failures / total, 2) if total > 0 else 0,
            "avg_retries": round(retries / max(completions + failures, 1), 2),
        }

    def get_learning_insights(self) -> Dict:
        """Get aggregate learning insights from all execution events.

        Use this to understand system-wide patterns.
        """
        conn = get_connection()
        cur = conn.cursor()

        # Overall stats
        cur.execute("""
            SELECT
                COUNT(*) as total_events,
                SUM(CASE WHEN event_type = 'complete' THEN 1 ELSE 0 END) as total_completions,
                SUM(CASE WHEN event_type = 'fail' THEN 1 ELSE 0 END) as total_failures,
                SUM(CASE WHEN event_type = 'retry' THEN 1 ELSE 0 END) as total_retries,
                SUM(CASE WHEN event_type = 'stuck' THEN 1 ELSE 0 END) as total_stuck,
                SUM(CASE WHEN event_type = 'verify' THEN 1 ELSE 0 END) as total_verifications
            FROM execution_events
        """)
        overall = cur.fetchone()

        # Average confidence over time
        cur.execute("""
            SELECT AVG(confidence) as avg_confidence
            FROM execution_events
            WHERE confidence IS NOT NULL
        """)
        conf_row = cur.fetchone()

        # Risk distribution
        cur.execute("""
            SELECT risk_level, COUNT(*) as count
            FROM execution_events
            WHERE risk_level IS NOT NULL
            GROUP BY risk_level
        """)
        risk_dist = {row["risk_level"]: row["count"] for row in cur.fetchall()}

        # Failure patterns - what event_types precede failures
        cur.execute("""
            SELECT event_type, COUNT(*) as count
            FROM execution_events
            WHERE event_type = 'stuck'
            GROUP BY event_type
        """)
        stuck_count = cur.fetchone()

        conn.close()

        total = overall["total_events"] if overall else 0
        completions = overall["total_completions"] if overall else 0
        failures = overall["total_failures"] if overall else 0

        return {
            "total_events": total,
            "overall_success_rate": round(completions / max(total, 1), 2),
            "overall_fail_rate": round(failures / max(total, 1), 2),
            "total_retries": overall["total_retries"] if overall else 0,
            "total_stuck": overall["total_stuck"] if overall else 0,
            "total_verifications": overall["total_verifications"] if overall else 0,
            "average_confidence": round(conf_row["avg_confidence"], 2) if conf_row and conf_row["avg_confidence"] else None,
            "risk_distribution": risk_dist,
            "recommendation": self._generate_learning_recommendation(
                total, completions, failures, overall
            ),
        }

    def _generate_learning_recommendation(self, total: int, completions: int,
                                          failures: int, overall: Optional[Dict]) -> str:
        """Generate a recommendation based on historical patterns."""
        if total < 5:
            return "Not enough data yet. Need at least 5 execution events for meaningful insights."

        fail_rate = failures / max(total, 1)
        stuck_count = overall["total_stuck"] if overall else 0

        recommendations = []

        if fail_rate > 0.3:
            recommendations.append(
                "High failure rate detected. Consider adding more verification steps "
                "or breaking complex steps into smaller ones."
            )

        if stuck_count > 2:
            recommendations.append(
                "Multiple stuck events detected. Consider adding timeouts or "
                "breaking long-running steps into checkpoints."
            )

        if fail_rate < 0.1 and total > 10:
            recommendations.append(
                "Execution is reliable. Consider increasing autonomy (higher max_steps)."
            )

        if not recommendations:
            return "System is performing within normal parameters."

        return " ".join(recommendations)

    # ─── Internal: Predictive Warnings ───────────────────────

    def _generate_prediction(self, step: Dict, plan: Optional[Dict]) -> Optional[str]:
        """Generate a predictive warning BEFORE executing a step.

        Uses historical execution_events to predict failure risk.
        Returns None if no warning needed, or a warning string.
        """
        learning = self._get_step_learning_patterns(step)
        if not learning or learning["sample_size"] < 3:
            return None

        fail_rate = learning["fail_rate"]
        sample_size = learning["sample_size"]
        avg_retries = learning["avg_retries"]

        parts = []

        # Failure rate warning
        if fail_rate > 0.4:
            parts.append(
                f"**⚠ Prediction:** This type of step has a **{int(fail_rate*100)}% failure rate** "
                f"based on {sample_size} similar past executions."
            )
        elif fail_rate > 0.2:
            parts.append(
                f"**💡 Heads up:** Similar steps have failed {int(fail_rate*100)}% of the time "
                f"({sample_size} past executions)."
            )

        # Retry pattern warning
        if avg_retries > 1.5:
            parts.append(
                f"Steps like this typically need **{avg_retries:.1f} retries** before succeeding."
            )

        # Check for common failure reasons from past events
        common_issues = self._get_common_failure_reasons(step)
        if common_issues:
            parts.append(f"Common issue: {common_issues}")

        # If we have a known successful pattern, suggest it
        pattern = self._get_successful_pattern(step)
        if pattern:
            parts.append(
                f"**💡 Known fix:** Previously solved by: {pattern['solution_summary']}"
            )
            if pattern.get("strategy"):
                parts.append(f"Suggested approach: {pattern['strategy']}")

        if not parts:
            return None

        return "\n".join(parts)

    def _get_common_failure_reasons(self, step: Dict) -> Optional[str]:
        """Query execution_events for common error messages in failed steps of this type."""
        step_type = self._classify_step_type(step)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT message, COUNT(*) as count
            FROM execution_events
            WHERE event_type = 'fail' AND message LIKE ?
            GROUP BY message
            ORDER BY count DESC
            LIMIT 1
        """, (f"%{step_type}%",))
        row = cur.fetchone()
        conn.close()

        if row and row["message"]:
            return row["message"][:200]
        return None

    # ─── Internal: Strategy Adaptation ───────────────────────

    ADAPTED_STRATEGIES = {
        "debug": {
            "default": "Reproduce issue → identify root cause → apply fix → verify",
            "adapted": "Run full diagnostic → check environment variables → inspect logs → regenerate tokens → test with clean state",
        },
        "auth": {
            "default": "Inspect headers → validate tokens → check permissions",
            "adapted": "Run full auth flow test → regenerate JWT secret → check token expiration → validate OAuth flow → test with fresh credentials",
        },
        "deploy": {
            "default": "Prepare environment → deploy → smoke test → monitor",
            "adapted": "Validate all configs → run pre-deploy checks → deploy to staging first → run integration tests → promote to production → monitor for 5 minutes",
        },
        "test": {
            "default": "Define test cases → execute → check results → report",
            "adapted": "Review existing tests → check test environment → run isolated tests first → then integration → capture full output for analysis",
        },
        "config": {
            "default": "Identify requirements → configure → validate settings",
            "adapted": "Backup current config → identify requirements → configure incrementally → validate after each change → run health check",
        },
    }

    def _get_adapted_strategy(self, step: Dict) -> Optional[str]:
        """Get an adapted strategy if this step type has high failure rates."""
        learning = self._get_step_learning_patterns(step)
        if not learning or learning["sample_size"] < 3:
            return None

        # Only adapt if failure rate is concerning
        if learning["fail_rate"] <= 0.3:
            return None

        step_type = self._classify_step_type(step)
        strategies = self.ADAPTED_STRATEGIES.get(step_type)
        if not strategies:
            return None

        return strategies.get("adapted")

    def _classify_step_type(self, step: Dict) -> str:
        """Classify a step into a type for learning/analytics."""
        title = (step.get("title") or "").lower()

        type_keywords = {
            "debug": ["debug", "fix", "diagnose", "troubleshoot"],
            "test": ["test", "verify", "validate", "check"],
            "deploy": ["deploy", "ship", "release"],
            "auth": ["auth", "login", "permission", "security"],
            "config": ["config", "setup", "set up", "configure"],
            "write": ["write", "create", "add", "build", "implement"],
            "review": ["review", "inspect", "audit"],
            "database": ["database", "db", "migration", "sql"],
        }
        for stype, keywords in type_keywords.items():
            for kw in keywords:
                if kw in title:
                    return stype
        return "general"

    # ─── Internal: Successful Patterns Memory ────────────────

    def _get_successful_pattern(self, step: Dict) -> Optional[Dict]:
        """Find a previously successful pattern using semantic similarity.

        "fix login bug" now matches "debug auth failure" because the semantic
        matcher recognizes synonyms and related concepts.
        """
        query = f"{step.get('title', '')} {step.get('description', '')}"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, step_type, step_title_pattern, solution_summary, strategy, success_count, last_used_at
            FROM successful_patterns
            WHERE success_count > 0
            ORDER BY success_count DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return None

        # Use semantic matching to find best candidates
        candidates = [dict(row) for row in rows]
        matches = find_best_matches(
            query=query,
            candidates=candidates,
            text_key="step_title_pattern",
            top_k=1,
            threshold=0.15,
        )

        if matches:
            return matches[0][0]  # best match

        return None

    def _record_successful_pattern(self, step: Dict, solution_summary: str, strategy: str = ""):
        """Record a successful solution pattern for future reuse."""
        step_type = self._classify_step_type(step)
        title = (step.get("title") or "").lower()

        conn = get_connection()
        cur = conn.cursor()

        # Check if similar pattern already exists
        cur.execute("""
            SELECT id, success_count FROM successful_patterns
            WHERE step_type = ? AND solution_summary = ?
            LIMIT 1
        """, (step_type, solution_summary))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE successful_patterns
                SET success_count = ?, last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (existing["success_count"] + 1, existing["id"]))
        else:
            cur.execute("""
                INSERT INTO successful_patterns (step_type, step_title_pattern, solution_summary, strategy)
                VALUES (?, ?, ?, ?)
            """, (step_type, title[:100], solution_summary, strategy))

        conn.commit()
        conn.close()

    def get_successful_patterns_summary(self) -> List[Dict]:
        """Get all successful patterns for analytics/display."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, step_type, step_title_pattern, solution_summary, strategy, success_count, last_used_at
            FROM successful_patterns
            ORDER BY success_count DESC, last_used_at DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ─── Internal: Long-Horizon Project Learning ─────────────

    def _classify_project_type(self, plan: Optional[Dict]) -> str:
        """Classify a plan/project into a type for long-horizon learning."""
        if not plan:
            return "general"

        title = (plan.get("title") or "").lower()
        goal = (plan.get("goal") or "").lower()
        combined = f"{title} {goal}"

        type_keywords = {
            "auth_system": ["auth", "login", "authentication", "oauth", "jwt", "credential"],
            "api_development": ["api", "endpoint", "rest", "graphql", "backend", "service"],
            "deployment": ["deploy", "ship", "release", "production", "ci/cd", "pipeline"],
            "database": ["database", "db", "migration", "schema", "sql", "postgres"],
            "frontend": ["frontend", "ui", "interface", "react", "vue", "component"],
            "security": ["security", "permission", "firewall", "vulnerability", "encrypt"],
            "performance": ["performance", "speed", "optimize", "cache", "latency", "scale"],
            "integration": ["integrate", "connect", "webhook", "third-party", "plugin"],
            "testing": ["test", "qa", "quality", "coverage", "ci"],
            "monitoring": ["monitor", "logging", "alert", "metric", "observability"],
        }

        for ptype, keywords in type_keywords.items():
            for kw in keywords:
                if kw in combined:
                    return ptype

        return "general"

    def _record_project_pattern(self, plan: Dict, failure_stage: str = "",
                                success_strategy: str = "", completed: bool = False):
        """Record project-level outcome for long-horizon learning."""
        project_type = self._classify_project_type(plan)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, total_plans, completed_plans, failed_plans, avg_steps_to_failure
            FROM project_patterns
            WHERE project_type = ?
            LIMIT 1
        """, (project_type,))
        existing = cur.fetchone()

        if existing:
            d = dict(existing)
            new_total = d["total_plans"] + 1
            new_completed = d["completed_plans"] + (1 if completed else 0)
            new_failed = d["failed_plans"] + (0 if completed else 1)

            cur.execute("""
                UPDATE project_patterns
                SET total_plans = ?, completed_plans = ?, failed_plans = ?,
                    failure_stage = ?, success_strategy = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_total, new_completed, new_failed,
                  failure_stage or d["failure_stage"],
                  success_strategy or d["success_strategy"],
                  d["id"]))
        else:
            cur.execute("""
                INSERT INTO project_patterns (project_type, failure_stage, success_strategy,
                                              total_plans, completed_plans, failed_plans)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (project_type, failure_stage, success_strategy,
                  1 if completed else 0, 0 if completed else 1))

        conn.commit()
        conn.close()

    def _get_project_insight(self, plan: Optional[Dict]) -> Optional[str]:
        """Get long-horizon insight about this type of project."""
        if not plan:
            return None

        project_type = self._classify_project_type(plan)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT project_type, failure_stage, success_stage, total_plans,
                   completed_plans, failed_plans, success_strategy, insight
            FROM project_patterns
            WHERE project_type = ? AND total_plans >= 2
            LIMIT 1
        """, (project_type,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        d = dict(row)
        total = d["total_plans"]
        failed = d["failed_plans"]
        completed = d["completed_plans"]

        if total < 2:
            return None

        fail_rate = failed / total if total > 0 else 0
        parts = []

        if fail_rate > 0.4 and d["failure_stage"]:
            parts.append(
                f"**⚠ Project insight:** {project_type.replace('_', ' ').title()} projects "
                f"tend to fail during the **{d['failure_stage']}** phase "
                f"({int(fail_rate*100)}% failure rate across {total} projects)."
            )

        if d["success_strategy"]:
            parts.append(
                f"**💡 Recommended:** {d['success_strategy']}"
            )

        if completed > 0 and d["success_stage"]:
            parts.append(
                f"Projects of this type succeed most when {d['success_stage']} is done carefully."
            )

        if not parts:
            return None

        return "\n".join(parts)

    def get_project_patterns_summary(self) -> List[Dict]:
        """Get all project patterns for analytics/display."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT project_type, failure_stage, success_stage, total_plans,
                   completed_plans, failed_plans, success_strategy, insight,
                   updated_at, created_at
            FROM project_patterns
            ORDER BY total_plans DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    KEYWORD_APPROACHES = {
        "debug": "Reproduce issue → identify root cause → apply fix → verify",
        "fix": "Reproduce issue → identify root cause → apply fix → verify",
        "diagnose": "Gather symptoms → isolate variables → identify root cause",
        "troubleshoot": "Reproduce → isolate → diagnose → fix → verify",
        "test": "Define test cases → execute → check results → report",
        "verify": "Check criteria → validate results → confirm",
        "validate": "Check criteria → validate results → confirm",
        "deploy": "Prepare environment → deploy → smoke test → monitor",
        "ship": "Final checks → deploy → monitor → rollback plan ready",
        "release": "Final checks → tag release → deploy → announce",
        "write": "Design → draft → review → refine",
        "create": "Design → implement → review → integrate",
        "add": "Identify location → implement → integrate → test",
        "build": "Design → implement → test → integrate",
        "implement": "Design → code → test → integrate",
        "review": "Gather inputs → evaluate against criteria → report findings",
        "check": "Gather inputs → evaluate → report",
        "inspect": "Gather inputs → evaluate → report",
        "audit": "Define scope → gather evidence → evaluate → report",
        "configure": "Identify requirements → configure → validate settings",
        "setup": "Identify requirements → set up → validate → document",
        "set up": "Identify requirements → set up → validate → document",
    }

    def _generate_step_thinking(self, step: Dict, plan: Optional[Dict]) -> str:
        """Generate thinking trace. Uses adapted strategy if available, then keywords, then LLM."""
        title = (step.get("title") or "").lower()
        desc = step.get("description", "")

        # Check for adapted strategy first (based on failure patterns)
        approach = self._get_adapted_strategy(step)
        is_adapted = approach is not None

        # Fall back to keyword matching
        if not approach:
            for keyword, pattern in self.KEYWORD_APPROACHES.items():
                if keyword in title:
                    approach = pattern
                    break

        # Fall back to LLM
        if not approach:
            approach = self._llm_generate_approach(step, plan)

        thinking = f"**Thinking:**\n"
        if desc:
            thinking += f"→ Goal: {desc}\n"
        else:
            thinking += f"→ Goal: Complete \"{step.get('title', 'this step')}\"\n"

        if is_adapted:
            thinking += f"→ Adapted approach (based on past failures): {approach}\n"
        else:
            thinking += f"→ Approach: {approach}\n"

        thinking += f"→ Action: Let's work through this step now.\n"

        return thinking

    def _llm_generate_approach(self, step: Dict, plan: Optional[Dict]) -> str:
        """Use LLM to generate an approach when keywords don't match."""
        try:
            plan_title = plan.get("title", "") if plan else ""
            result = self.llm_service.simple_chat(
                f"Step: {step.get('title', '')}\nDescription: {step.get('description', '')}\nPlan: {plan_title}",
                system_prompt=(
                    "You are an execution planner. Given a step in a plan, describe the approach "
                    "in one line using arrows (→). Example: 'Gather data → analyze → report findings'. "
                    "Reply with ONLY the approach line, no other text."
                ),
            )
            approach = result.get("content", "").strip()
            # Clean up - take first line only
            approach = approach.split("\n")[0].strip()
            if approach:
                return approach
        except Exception:
            pass

        return "Analyze → execute → verify"

    # ─── Internal: Plan Finding ──────────────────────────────

    def _find_active_plan(self, conversation_id: int) -> Optional[Dict]:
        plans = self.planning_service.list_plans(
            conversation_id=conversation_id, status="active", limit=1
        )
        if plans:
            return plans[0]

        plans = self.planning_service.list_plans(
            conversation_id=conversation_id, status="draft", limit=1
        )
        if plans:
            return plans[0]

        plans = self.planning_service.list_plans(status="active", limit=1)
        if plans:
            return plans[0]

        plans = self.planning_service.list_plans(status="draft", limit=1)
        if plans:
            return plans[0]

        return None

    # ─── Internal: Response Formatting ───────────────────────

    def _format_step_response(self, step: Dict, progress: Dict, action: str,
                              thinking: str = "", confidence: float = 0.7,
                              risk: str = "medium",
                              prediction: Optional[str] = None,
                              known_pattern: Optional[Dict] = None,
                              project_insight: Optional[str] = None) -> str:
        counts = progress.get("counts", {})
        total = counts.get("total_steps", 0)
        done = counts.get("completed", 0)

        if action == "starting":
            header = f"**Executing:** {progress.get('plan', {}).get('title', 'Plan')}\n"
        elif action == "resuming":
            header = f"**Resumed:** {progress.get('plan', {}).get('title', 'Plan')}\n"
        else:
            header = f"**✓ Step completed** ({done}/{total})\n"

        step_text = f"{header}\n"

        # Project-level insight (long-horizon learning)
        if project_insight:
            step_text += f"{project_insight}\n\n"

        # Predictive warning (before thinking)
        if prediction:
            step_text += f"{prediction}\n\n"

        # Known successful pattern (semantic match)
        if known_pattern:
            step_text += (
                f"**💡 Known solution:** {known_pattern['solution_summary']}\n"
                f"(Used successfully {known_pattern['success_count']} time{'s' if known_pattern['success_count'] != 1 else ''})\n\n"
            )

        if thinking:
            step_text += f"{thinking}\n"

        # Confidence and risk indicators
        conf_bar = "●" * int(confidence * 5) + "○" * (5 - int(confidence * 5))
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
        step_text += f"**Confidence:** {conf_bar} {int(confidence*100)}%  |  **Risk:** {risk_icon} {risk}\n\n"

        step_text += f"**Step {step.get('step_order', '?')}:** {step.get('title', 'Unknown')}\n"
        if step.get("description"):
            step_text += f"{step['description']}\n"

        remaining = total - done
        if remaining > 0:
            step_text += f"\n*{remaining} step{'s' if remaining != 1 else ''} remaining. Say 'continue' when done, 'pause' to hold.*"

        return step_text

    # ─── Internal: DB Persistence ────────────────────────────

    def _get_session(self, conversation_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM execution_sessions WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        try:
            d["step_log"] = json.loads(d["step_log"]) if d["step_log"] else []
        except Exception:
            d["step_log"] = []
        return d

    def _upsert_session(self, conversation_id: int, plan_id: int,
                        current_step_id: int, current_execution_id: int,
                        status: str = "running"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO execution_sessions (conversation_id, plan_id, current_step_id, current_execution_id, status, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(conversation_id) DO UPDATE SET
                plan_id = excluded.plan_id,
                current_step_id = excluded.current_step_id,
                current_execution_id = excluded.current_execution_id,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
        """, (conversation_id, plan_id, current_step_id, current_execution_id, status))
        conn.commit()
        conn.close()

    def _update_session_status(self, conversation_id: int, status: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE execution_sessions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?",
            (status, conversation_id)
        )
        conn.commit()
        conn.close()

    def _append_step_log(self, conversation_id: int, session: Dict, entry: Dict):
        log = session.get("step_log", [])
        log.append(entry)
        log = log[-50:]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE execution_sessions SET step_log = ?, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?",
            (json.dumps(log), conversation_id)
        )
        conn.commit()
        conn.close()

    def _get_step_log(self, session: Dict) -> List[Dict]:
        return session.get("step_log", [])

    # ─── Internal: Event Logging (analytics table) ───────────

    def _log_event(self, execution_id: Optional[int], step_id: Optional[int],
                   plan_id: int, event_type: str, message: str = "",
                   confidence: Optional[float] = None, risk_level: str = "medium"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO execution_events (execution_id, step_id, plan_id, event_type, message, confidence, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (execution_id, step_id, plan_id, event_type, message, confidence, risk_level))
        conn.commit()
        conn.close()

    def _get_recent_events(self, plan_id: int, limit: int = 10) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, execution_id, step_id, plan_id, event_type, message, confidence, risk_level, created_at
            FROM execution_events
            WHERE plan_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """, (plan_id, limit))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_plan_analytics(self, plan_id: int) -> Dict:
        """Get analytics for a plan from execution_events."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT event_type, COUNT(*) as count
            FROM execution_events
            WHERE plan_id = ?
            GROUP BY event_type
        """, (plan_id,))
        type_counts = {row["event_type"]: row["count"] for row in cur.fetchall()}

        cur.execute("""
            SELECT AVG(confidence) as avg_confidence
            FROM execution_events
            WHERE plan_id = ? AND confidence IS NOT NULL
        """, (plan_id,))
        avg_conf_row = cur.fetchone()
        avg_confidence = avg_conf_row["avg_confidence"] if avg_conf_row else None

        cur.execute("""
            SELECT risk_level, COUNT(*) as count
            FROM execution_events
            WHERE plan_id = ? AND risk_level IS NOT NULL
            GROUP BY risk_level
        """, (plan_id,))
        risk_counts = {row["risk_level"]: row["count"] for row in cur.fetchall()}

        cur.execute("""
            SELECT COUNT(*) as total FROM execution_events WHERE plan_id = ?
        """, (plan_id,))
        total_row = cur.fetchone()
        total_events = total_row["total"] if total_row else 0

        conn.close()

        return {
            "plan_id": plan_id,
            "total_events": total_events,
            "event_type_counts": type_counts,
            "average_confidence": round(avg_confidence, 2) if avg_confidence else None,
            "risk_distribution": risk_counts,
        }

    # ─── System Prompt ───────────────────────────────────────

    def build_execution_system_prompt(self, base_prompt: str, execution_state: Dict) -> str:
        plan = self.planning_service.get_plan_by_id(execution_state["plan_id"])
        step = self.planning_service.get_plan_step_by_id(execution_state["step_id"])
        progress = self.planning_service.get_plan_progress_summary(execution_state["plan_id"])

        if not plan or not step or not progress:
            return base_prompt

        counts = progress["counts"]
        steps = self.planning_service.list_plan_steps(execution_state["plan_id"])

        step_list = ""
        for s in steps:
            marker = "→" if s["id"] == step["id"] else ("✓" if s["status"] == "completed" else "○")
            step_list += f"  {marker} Step {s['step_order']}: {s['title']} [{s['status']}]\n"

        confidence, risk = self._assess_step(step, plan)

        # ── Intelligence injection ─────────────────────────────
        intel_sections = []

        # Prediction context
        prediction = self._generate_prediction(step, plan)
        if prediction:
            intel_sections.append(
                f"PREDICTION:\n{prediction}\n"
                f"Use this to warn the user and suggest preventive actions."
            )

        # Known solution
        known = self._get_successful_pattern(step)
        if known:
            intel_sections.append(
                f"KNOWN SOLUTION (used {known['success_count']} times successfully):\n"
                f"{known['solution_summary']}\n"
                f"{'Strategy: ' + known['strategy'] if known.get('strategy') else ''}\n"
                f"Prioritize this approach — it has a proven track record."
            )

        # Adapted strategy
        adapted = self._get_adapted_strategy(step)
        if adapted:
            intel_sections.append(
                f"ADAPTED STRATEGY (based on high failure rate of similar steps):\n"
                f"{adapted}\n"
                f"Use this instead of the default approach."
            )

        # Project insight
        project_insight = self._get_project_insight(plan)
        if project_insight:
            intel_sections.append(
                f"PROJECT-LEVEL INSIGHT:\n{project_insight}\n"
                f"Factor this into your guidance."
            )

        # Learning patterns
        learning = self._get_step_learning_patterns(step)
        if learning and learning["sample_size"] >= 3:
            intel_sections.append(
                f"HISTORICAL DATA ({learning['sample_size']} similar executions):\n"
                f"  Success rate: {int(learning['success_rate']*100)}%\n"
                f"  Fail rate: {int(learning['fail_rate']*100)}%\n"
                f"  Avg retries: {learning['avg_retries']}\n"
                f"{'  This step type struggles — be extra careful and suggest verification.' if learning['fail_rate'] > 0.3 else ''}"
            )

        intel_block = ""
        if intel_sections:
            intel_block = "\nINTELLIGENCE (use this to inform your response):\n" + "\n".join(intel_sections) + "\n"
        # ────────────────────────────────────────────────────────

        return (
            f"You are Mnemosyne AI in EXECUTION MODE.\n\n"
            f"ACTIVE PLAN: {plan['title']}\n"
            f"GOAL: {plan.get('goal', 'N/A')}\n\n"
            f"STEPS:\n{step_list}\n"
            f"CURRENT STEP: Step {step['step_order']}: {step['title']}\n"
            f"DESCRIPTION: {step.get('description', 'N/A')}\n"
            f"CONFIDENCE: {confidence} | RISK: {risk}\n\n"
            f"PROGRESS: {counts['completed']}/{counts['total_steps']} done ({progress['percent_complete']}%)\n"
            f"{intel_block}\n"
            f"RULES:\n"
            f"- Focus ONLY on the current step.\n"
            f"- Give concrete, actionable guidance for this step.\n"
            f"- Show your thinking: hypothesis → action → expected result.\n"
            f"- Reference the intelligence above — mention predictions, known solutions, and historical patterns.\n"
            f"- If a known solution exists, recommend it explicitly.\n"
            f"- If risk is high, warn the user before suggesting aggressive actions.\n"
            f"- If confidence is low, state what you're uncertain about.\n"
            f"- Do NOT discuss other topics, projects, or memories.\n"
            f"- Do NOT ask the user which step to do — the system handles that.\n"
            f"- When the user says 'continue' or 'done', the system will advance automatically.\n"
            f"- Be direct and task-focused. No small talk."
        )
