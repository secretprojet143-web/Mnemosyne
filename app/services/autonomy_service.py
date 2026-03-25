from typing import List, Dict, Optional

from app.db.database import get_connection
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService


class AutonomyService:
    def __init__(self):
        self.planning_service = PlanningService()
        self.execution_service = ExecutionService()

    def create_autonomy_run(
        self,
        plan_id: int,
        reasoning_state_id: Optional[int] = None,
        status: str = "draft",
        max_steps: int = 10,
        steps_executed: int = 0,
        max_tool_calls: int = 20,
        tool_calls_used: int = 0,
        stop_reason: str = ""
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO autonomy_runs (
                plan_id,
                reasoning_state_id,
                status,
                max_steps,
                steps_executed,
                max_tool_calls,
                tool_calls_used,
                stop_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            reasoning_state_id,
            status,
            max_steps,
            steps_executed,
            max_tool_calls,
            tool_calls_used,
            stop_reason.strip()
        ))

        run_id = cur.lastrowid
        conn.commit()
        conn.close()

        return run_id

    def get_autonomy_run_by_id(self, run_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                plan_id,
                reasoning_state_id,
                status,
                max_steps,
                steps_executed,
                max_tool_calls,
                tool_calls_used,
                stop_reason,
                created_at,
                updated_at
            FROM autonomy_runs
            WHERE id = ?
        """, (run_id,))

        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def list_autonomy_runs(
        self,
        status: Optional[str] = None,
        plan_id: Optional[int] = None,
        reasoning_state_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                id,
                plan_id,
                reasoning_state_id,
                status,
                max_steps,
                steps_executed,
                max_tool_calls,
                tool_calls_used,
                stop_reason,
                created_at,
                updated_at
            FROM autonomy_runs
        """
        conditions = []
        params = []

        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if plan_id is not None:
            conditions.append("plan_id = ?")
            params.append(plan_id)

        if reasoning_state_id is not None:
            conditions.append("reasoning_state_id = ?")
            params.append(reasoning_state_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_autonomy_run(
        self,
        run_id: int,
        status: Optional[str] = None,
        max_steps: Optional[int] = None,
        steps_executed: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        tool_calls_used: Optional[int] = None,
        stop_reason: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_autonomy_run_by_id(run_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE autonomy_runs
            SET
                status = ?,
                max_steps = ?,
                steps_executed = ?,
                max_tool_calls = ?,
                tool_calls_used = ?,
                stop_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            status if status is not None else existing["status"],
            max_steps if max_steps is not None else existing["max_steps"],
            steps_executed if steps_executed is not None else existing["steps_executed"],
            max_tool_calls if max_tool_calls is not None else existing["max_tool_calls"],
            tool_calls_used if tool_calls_used is not None else existing["tool_calls_used"],
            stop_reason.strip() if stop_reason is not None else existing["stop_reason"],
            run_id
        ))

        conn.commit()
        conn.close()

        return self.get_autonomy_run_by_id(run_id)

    def autonomy_run_exists(self, run_id: int) -> bool:
        return self.get_autonomy_run_by_id(run_id) is not None

    # --------------------
    # Environment & Readiness
    # --------------------
    def get_environment_snapshot(self, run_id: int) -> Optional[Dict]:
        run = self.get_autonomy_run_by_id(run_id)
        if not run:
            return None

        plan_id = run["plan_id"]

        plan_summary = self.planning_service.get_plan_progress_summary(plan_id)
        plan_health = self.planning_service.get_plan_health_summary(plan_id)
        execution_health = self.planning_service.get_plan_execution_health_summary(plan_id)
        ready_steps = self.planning_service.get_ready_steps(plan_id)
        blocked_steps = self.planning_service.get_blocked_steps(plan_id)

        return {
            "run": run,
            "plan_summary": plan_summary,
            "plan_health": plan_health,
            "execution_health": execution_health,
            "ready_steps": ready_steps,
            "blocked_steps": blocked_steps
        }

    def evaluate_run_readiness(self, run_id: int) -> Optional[Dict]:
        snapshot = self.get_environment_snapshot(run_id)
        if not snapshot:
            return None

        run = snapshot["run"]
        plan_health = snapshot["plan_health"]
        execution_health = snapshot["execution_health"]
        ready_steps = snapshot["ready_steps"]

        reasons = []
        can_proceed = True

        if run["steps_executed"] >= run["max_steps"]:
            can_proceed = False
            reasons.append("Step budget exhausted.")

        if run["tool_calls_used"] >= run["max_tool_calls"]:
            can_proceed = False
            reasons.append("Tool call budget exhausted.")

        if run["status"] not in {"draft", "running", "paused"}:
            can_proceed = False
            reasons.append(f"Run status '{run['status']}' is not executable.")

        if plan_health and plan_health["health_status"] == "blocked":
            can_proceed = False
            reasons.append("Plan is structurally blocked.")

        if execution_health and execution_health["execution_health_status"] == "requires_intervention":
            can_proceed = False
            reasons.append("Execution failures require manual intervention.")

        if not ready_steps:
            can_proceed = False
            reasons.append("No ready steps available.")

        recovery_hint = None
        if execution_health and execution_health["execution_health_status"] == "retryable_failures":
            recovery_hint = execution_health.get("next_execution_action")
            reasons.append("Plan has retryable failed step(s) that may need attention before new execution.")

        return {
            "run_id": run_id,
            "can_proceed": can_proceed,
            "reasons": reasons,
            "recovery_hint": recovery_hint,
            "next_ready_step": ready_steps[0] if ready_steps else None,
            "budgets": {
                "steps_executed": run["steps_executed"],
                "max_steps": run["max_steps"],
                "tool_calls_used": run["tool_calls_used"],
                "max_tool_calls": run["max_tool_calls"]
            },
            "plan_health_status": plan_health["health_status"] if plan_health else None,
            "execution_health_status": execution_health["execution_health_status"] if execution_health else None
        }

    # --------------------
    # Autonomy Lifecycle
    # --------------------
    def pause_run(self, run_id: int, reason: str = "") -> Optional[Dict]:
        return self.update_autonomy_run(
            run_id=run_id,
            status="paused",
            stop_reason=reason or "Run paused."
        )

    def resume_run(self, run_id: int) -> Optional[Dict]:
        run = self.get_autonomy_run_by_id(run_id)
        if not run:
            return None

        if run["status"] != "paused":
            raise ValueError("Only paused runs can be resumed.")

        return self.update_autonomy_run(
            run_id=run_id,
            status="running",
            stop_reason=""
        )

    def complete_run(self, run_id: int, reason: str = "") -> Optional[Dict]:
        return self.update_autonomy_run(
            run_id=run_id,
            status="completed",
            stop_reason=reason or "Run completed successfully."
        )

    def handoff_run(self, run_id: int, reason: str = "") -> Optional[Dict]:
        return self.update_autonomy_run(
            run_id=run_id,
            status="paused",
            stop_reason=reason or "Run handed off for human review."
        )

    def build_handoff_summary(self, run_id: int) -> Optional[Dict]:
        snapshot = self.get_environment_snapshot(run_id)
        if not snapshot:
            return None

        run = snapshot["run"]
        plan_health = snapshot["plan_health"]
        execution_health = snapshot["execution_health"]

        recommended_human_action = "inspect_workflow_state"
        if execution_health and execution_health.get("execution_health_status") == "requires_intervention":
            recommended_human_action = "inspect_failed_execution_and_fix_inputs_or_permissions"
        elif plan_health and plan_health.get("health_status") == "blocked":
            recommended_human_action = "resolve_blocking_dependency"

        return {
            "run_id": run_id,
            "run_status": run["status"],
            "stop_reason": run["stop_reason"],
            "plan_health_status": plan_health["health_status"] if plan_health else None,
            "execution_health_status": execution_health["execution_health_status"] if execution_health else None,
            "recommended_human_action": recommended_human_action,
            "next_ready_step": snapshot["ready_steps"][0] if snapshot["ready_steps"] else None,
            "blocked_steps_count": len(snapshot["blocked_steps"]),
            "ready_steps_count": len(snapshot["ready_steps"])
        }

    # --------------------
    # Autonomy Decision Policy
    # --------------------
    def select_next_autonomy_action(self, run_id: int) -> Optional[Dict]:
        readiness = self.evaluate_run_readiness(run_id)
        if not readiness:
            return None

        if not readiness["can_proceed"]:
            reason_text = "; ".join(readiness["reasons"])

            if readiness.get("execution_health_status") == "requires_intervention":
                return {
                    "action_type": "handoff",
                    "reason": reason_text,
                    "target": None,
                    "readiness": readiness
                }

            return {
                "action_type": "stop",
                "reason": reason_text,
                "target": None,
                "readiness": readiness
            }

        recovery_hint = readiness.get("recovery_hint")
        if recovery_hint and recovery_hint.get("type") == "retry_step":
            return {
                "action_type": "retry_execution",
                "reason": "Retryable failed step should be retried before advancing.",
                "target": recovery_hint,
                "readiness": readiness
            }

        next_ready_step = readiness.get("next_ready_step")
        if next_ready_step:
            return {
                "action_type": "start_ready_step",
                "reason": "Next ready step is available.",
                "target": next_ready_step,
                "readiness": readiness
            }

        return {
            "action_type": "stop",
            "reason": "No actionable next step available.",
            "target": None,
            "readiness": readiness
        }

    # --------------------
    # Single-Step Autonomy Runtime
    # --------------------
    def _build_step_status_message(self, executed: bool, decision: Dict, step: Optional[Dict], execution: Optional[Dict]) -> str:
        action_type = decision.get("action_type", "unknown")

        if not executed:
            if action_type == "stop":
                return f"Stopped: {decision.get('reason', 'No reason provided.')}"
            if action_type == "handoff":
                return f"Handed off for human review: {decision.get('reason', 'Needs manual intervention.')}"
            return f"Not executed: {decision.get('reason', 'Unknown reason.')}"

        if step and execution:
            step_title = step.get("title", "Unknown step")
            attempt = execution.get("attempt_number", 1)
            if action_type == "retry_execution":
                return f"Retrying step '{step_title}' (attempt #{attempt}). Execution started."
            return f"Starting step '{step_title}' (attempt #{attempt}). Execution started."

        return "Step executed."

    def run_next_step(self, run_id: int) -> Optional[Dict]:
        run = self.get_autonomy_run_by_id(run_id)
        if not run:
            return None

        decision = self.select_next_autonomy_action(run_id)
        if not decision:
            return None

        action_type = decision["action_type"]

        if action_type == "stop":
            updated_run = self.update_autonomy_run(
                run_id=run_id,
                status="stopped",
                stop_reason=decision["reason"]
            )
            return {
                "run_id": run_id,
                "executed": False,
                "decision": decision,
                "execution": None,
                "step": None,
                "autonomy_run": updated_run,
                "handoff_summary": None,
                "step_status_message": self._build_step_status_message(False, decision, None, None)
            }

        if action_type == "handoff":
            updated_run = self.handoff_run(
                run_id=run_id,
                reason=decision["reason"]
            )
            handoff_summary = self.build_handoff_summary(run_id)

            return {
                "run_id": run_id,
                "executed": False,
                "decision": decision,
                "execution": None,
                "step": None,
                "autonomy_run": updated_run,
                "handoff_summary": handoff_summary,
                "step_status_message": self._build_step_status_message(False, decision, None, None)
            }

        if action_type == "retry_execution":
            target = decision["target"]
            previous_execution_id = target["execution_id"]
            previous_execution = self.execution_service.get_step_execution_by_id(previous_execution_id)
            if not previous_execution:
                updated_run = self.update_autonomy_run(
                    run_id=run_id,
                    status="stopped",
                    stop_reason="Retry target execution not found."
                )
                return {
                    "run_id": run_id,
                    "executed": False,
                    "decision": decision,
                    "execution": None,
                    "step": None,
                    "autonomy_run": updated_run,
                    "step_status_message": "Stopped: Retry target execution not found."
                }

            new_execution_id = self.execution_service.create_step_execution(
                plan_id=previous_execution["plan_id"],
                step_id=previous_execution["step_id"],
                action_type=previous_execution["action_type"],
                action_payload=previous_execution["action_payload"],
                status="pending",
                verification_status="unverified"
            )

            execution = self.execution_service.start_execution(new_execution_id)
            step = self.planning_service.get_plan_step_by_id(previous_execution["step_id"])

            updated_run = self.update_autonomy_run(
                run_id=run_id,
                status="running",
                steps_executed=run["steps_executed"] + 1,
                stop_reason=""
            )

            return {
                "run_id": run_id,
                "executed": True,
                "decision": decision,
                "execution": execution,
                "step": step,
                "autonomy_run": updated_run,
                "step_status_message": self._build_step_status_message(True, decision, step, execution)
            }

        if action_type == "start_ready_step":
            next_step = decision["target"]

            execution_id = self.execution_service.create_step_execution(
                plan_id=run["plan_id"],
                step_id=next_step["id"],
                action_type="autonomy_step",
                action_payload={
                    "source": "autonomy_runtime",
                    "run_id": run_id,
                    "step_title": next_step["title"]
                },
                status="pending",
                verification_status="unverified"
            )

            execution = self.execution_service.start_execution(execution_id)

            updated_run = self.update_autonomy_run(
                run_id=run_id,
                status="running",
                steps_executed=run["steps_executed"] + 1,
                stop_reason=""
            )

            return {
                "run_id": run_id,
                "executed": True,
                "decision": decision,
                "execution": execution,
                "step": next_step,
                "autonomy_run": updated_run,
                "step_status_message": self._build_step_status_message(True, decision, next_step, execution)
            }

        updated_run = self.update_autonomy_run(
            run_id=run_id,
            status="failed",
            stop_reason=f"Unknown autonomy action type: {action_type}"
        )
        return {
            "run_id": run_id,
            "executed": False,
            "decision": decision,
            "execution": None,
            "step": None,
            "autonomy_run": updated_run,
            "step_status_message": f"Failed: Unknown action type '{action_type}'."
        }
