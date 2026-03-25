import json
from datetime import datetime
from typing import List, Dict, Optional

from app.db.database import get_connection
from app.services.planning_service import PlanningService


class ExecutionService:
    def __init__(self):
        self.planning_service = PlanningService()

    def create_step_execution(
        self,
        plan_id: int,
        step_id: int,
        action_type: str = "manual",
        action_payload: Optional[Dict] = None,
        status: str = "pending",
        verification_status: str = "unverified"
    ) -> Optional[int]:
        step = self.planning_service.get_plan_step_by_id(step_id)
        if not step or step["plan_id"] != plan_id:
            return None

        attempt_number = self._next_attempt_number(step_id)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO step_executions (
                plan_id,
                step_id,
                attempt_number,
                action_type,
                action_payload,
                status,
                verification_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            step_id,
            attempt_number,
            action_type,
            json.dumps(action_payload or {}),
            status,
            verification_status
        ))

        execution_id = cur.lastrowid
        conn.commit()
        conn.close()

        return execution_id

    def get_step_execution_by_id(self, execution_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                plan_id,
                step_id,
                attempt_number,
                action_type,
                action_payload,
                status,
                result_summary,
                verification_status,
                error_message,
                started_at,
                finished_at,
                created_at,
                updated_at
            FROM step_executions
            WHERE id = ?
        """, (execution_id,))

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return self._decode_execution(dict(row))

    def list_step_executions(
        self,
        plan_id: Optional[int] = None,
        step_id: Optional[int] = None,
        status: Optional[str] = None,
        verification_status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                id,
                plan_id,
                step_id,
                attempt_number,
                action_type,
                action_payload,
                status,
                result_summary,
                verification_status,
                error_message,
                started_at,
                finished_at,
                created_at,
                updated_at
            FROM step_executions
        """
        conditions = []
        params = []

        if plan_id is not None:
            conditions.append("plan_id = ?")
            params.append(plan_id)

        if step_id is not None:
            conditions.append("step_id = ?")
            params.append(step_id)

        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if verification_status is not None:
            conditions.append("verification_status = ?")
            params.append(verification_status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return [self._decode_execution(dict(row)) for row in rows]

    def update_step_execution(
        self,
        execution_id: int,
        status: Optional[str] = None,
        result_summary: Optional[str] = None,
        verification_status: Optional[str] = None,
        error_message: Optional[str] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_step_execution_by_id(execution_id)
        if not existing:
            return None

        new_status = status if status is not None else existing["status"]
        new_verification_status = (
            verification_status if verification_status is not None else existing["verification_status"]
        )

        if not self._is_valid_execution_status_transition(existing["status"], new_status):
            raise ValueError(f"Invalid execution status transition: {existing['status']} -> {new_status}")

        if not self._is_valid_verification_transition(existing["verification_status"], new_verification_status):
            raise ValueError(
                f"Invalid verification status transition: {existing['verification_status']} -> {new_verification_status}"
            )

        if not self._is_verification_state_semantically_valid(new_status, new_verification_status):
            raise ValueError(
                f"Verification status '{new_verification_status}' is not valid for execution status '{new_status}'."
            )

        auto_started_at = existing["started_at"]
        auto_finished_at = existing["finished_at"]

        if new_status == "running" and not auto_started_at and started_at is None:
            auto_started_at = datetime.now().isoformat()

        if new_status in {"succeeded", "failed", "cancelled"} and not auto_finished_at and finished_at is None:
            auto_finished_at = datetime.now().isoformat()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE step_executions
            SET
                status = ?,
                result_summary = ?,
                verification_status = ?,
                error_message = ?,
                started_at = ?,
                finished_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            new_status,
            result_summary if result_summary is not None else existing["result_summary"],
            new_verification_status,
            error_message if error_message is not None else existing["error_message"],
            started_at if started_at is not None else auto_started_at,
            finished_at if finished_at is not None else auto_finished_at,
            execution_id
        ))

        conn.commit()
        conn.close()

        return self.get_step_execution_by_id(execution_id)

    def execution_exists(self, execution_id: int) -> bool:
        return self.get_step_execution_by_id(execution_id) is not None

    def _next_attempt_number(self, step_id: int) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT MAX(attempt_number) as max_attempt
            FROM step_executions
            WHERE step_id = ?
        """, (step_id,))

        row = cur.fetchone()
        conn.close()

        max_attempt = row["max_attempt"] if row and row["max_attempt"] is not None else 0
        return max_attempt + 1

    def _decode_execution(self, item: Dict) -> Dict:
        try:
            item["action_payload"] = json.loads(item["action_payload"]) if item["action_payload"] else {}
        except Exception:
            item["action_payload"] = {}

        return item

    # --------------------
    # Transition Validation
    # --------------------
    def _is_valid_execution_status_transition(self, current_status: str, new_status: str) -> bool:
        allowed = {
            "pending": {"running", "cancelled"},
            "running": {"succeeded", "failed", "cancelled"},
            "succeeded": set(),
            "failed": set(),
            "cancelled": set(),
        }
        return new_status == current_status or new_status in allowed.get(current_status, set())

    def _is_valid_verification_transition(self, current_verification: str, new_verification: str) -> bool:
        allowed = {
            "unverified": {"verified", "verification_failed"},
            "verified": set(),
            "verification_failed": set(),
        }
        return new_verification == current_verification or new_verification in allowed.get(current_verification, set())

    def _is_verification_state_semantically_valid(self, execution_status: str, verification_status: str) -> bool:
        if verification_status == "verified":
            return execution_status == "succeeded"

        if verification_status == "verification_failed":
            return execution_status in {"succeeded", "failed", "cancelled"}

        return True

    # --------------------
    # Execution-to-Step Sync
    # --------------------
    def sync_step_status_from_execution(self, execution_id: int) -> Optional[Dict]:
        execution = self.get_step_execution_by_id(execution_id)
        if not execution:
            return None

        step = self.planning_service.get_plan_step_by_id(execution["step_id"])
        if not step:
            return None

        target_status = None

        if execution["status"] == "running":
            target_status = "in_progress"

        elif execution["status"] == "failed":
            target_status = "failed"

        elif execution["status"] == "cancelled":
            if step["status"] == "in_progress":
                target_status = "pending"

        elif execution["status"] == "succeeded":
            if execution["verification_status"] == "verified":
                target_status = "completed"
            elif step["status"] == "pending":
                target_status = "in_progress"

        if target_status and target_status != step["status"]:
            updated_step = self.planning_service.update_plan_step(
                step_id=step["id"],
                status=target_status
            )
            return {
                "execution": execution,
                "step": updated_step,
                "synced": True,
                "new_step_status": target_status
            }

        return {
            "execution": execution,
            "step": step,
            "synced": False,
            "new_step_status": step["status"]
        }

    # --------------------
    # Convenience Lifecycle Methods
    # --------------------
    def start_execution(self, execution_id: int) -> Optional[Dict]:
        execution = self.update_step_execution(
            execution_id=execution_id,
            status="running"
        )
        if not execution:
            return None
        self.sync_step_status_from_execution(execution_id)
        return self.get_step_execution_by_id(execution_id)

    def mark_execution_succeeded(
        self,
        execution_id: int,
        result_summary: str = ""
    ) -> Optional[Dict]:
        execution = self.update_step_execution(
            execution_id=execution_id,
            status="succeeded",
            result_summary=result_summary
        )
        if not execution:
            return None
        self.sync_step_status_from_execution(execution_id)
        return self.get_step_execution_by_id(execution_id)

    def mark_execution_failed(
        self,
        execution_id: int,
        error_message: str = "",
        result_summary: str = ""
    ) -> Optional[Dict]:
        execution = self.update_step_execution(
            execution_id=execution_id,
            status="failed",
            error_message=error_message,
            result_summary=result_summary
        )
        if not execution:
            return None
        self.sync_step_status_from_execution(execution_id)
        return self.get_step_execution_by_id(execution_id)

    def mark_execution_cancelled(
        self,
        execution_id: int,
        result_summary: str = ""
    ) -> Optional[Dict]:
        execution = self.update_step_execution(
            execution_id=execution_id,
            status="cancelled",
            result_summary=result_summary
        )
        if not execution:
            return None
        self.sync_step_status_from_execution(execution_id)
        return self.get_step_execution_by_id(execution_id)

    def mark_execution_verified(self, execution_id: int) -> Optional[Dict]:
        execution = self.update_step_execution(
            execution_id=execution_id,
            verification_status="verified"
        )
        if not execution:
            return None
        self.sync_step_status_from_execution(execution_id)
        return self.get_step_execution_by_id(execution_id)

    def mark_execution_verification_failed(
        self,
        execution_id: int,
        error_message: str = ""
    ) -> Optional[Dict]:
        execution = self.update_step_execution(
            execution_id=execution_id,
            verification_status="verification_failed",
            error_message=error_message
        )
        if not execution:
            return None
        self.sync_step_status_from_execution(execution_id)
        return self.get_step_execution_by_id(execution_id)

    # --------------------
    # Failure Classification & Recovery
    # --------------------
    def classify_execution_failure(self, execution: Dict) -> Dict:
        error_message = (execution.get("error_message") or "").strip().lower()

        if not error_message:
            return {
                "failure_type": "unknown",
                "retryable": False,
                "reason": "No error message available."
            }

        retryable_terms = [
            "timeout",
            "temporary",
            "network",
            "rate limit",
            "unavailable",
            "connection reset",
            "connection error",
            "try again"
        ]

        non_retryable_terms = [
            "invalid",
            "unauthorized",
            "permission",
            "schema",
            "not found",
            "malformed",
            "forbidden",
            "missing required"
        ]

        if any(term in error_message for term in retryable_terms):
            return {
                "failure_type": "retryable",
                "retryable": True,
                "reason": "Failure appears transient or temporary."
            }

        if any(term in error_message for term in non_retryable_terms):
            return {
                "failure_type": "non_retryable",
                "retryable": False,
                "reason": "Failure appears structural or permission-related."
            }

        return {
            "failure_type": "unknown",
            "retryable": True,
            "reason": "Failure type is unclear; one cautious retry may be reasonable."
        }

    def get_step_execution_attempts(self, step_id: int) -> List[Dict]:
        return self.list_step_executions(step_id=step_id, limit=100)

    def get_execution_recovery_recommendation(self, execution_id: int) -> Optional[Dict]:
        execution = self.get_step_execution_by_id(execution_id)
        if not execution:
            return None

        step_attempts = self.get_step_execution_attempts(execution["step_id"])
        attempt_count = len(step_attempts)

        classification = self.classify_execution_failure(execution)

        recommended_action = "inspect_manually"
        can_retry = False

        if execution["status"] != "failed":
            recommended_action = "no_recovery_needed"
        else:
            if classification["failure_type"] == "retryable":
                can_retry = attempt_count < 3
                recommended_action = "retry" if can_retry else "escalate"
            elif classification["failure_type"] == "non_retryable":
                can_retry = False
                recommended_action = "revise_input_or_permissions"
            else:
                can_retry = attempt_count < 2
                recommended_action = "retry_once_cautiously" if can_retry else "inspect_manually"

        return {
            "execution_id": execution_id,
            "step_id": execution["step_id"],
            "plan_id": execution["plan_id"],
            "attempt_number": execution["attempt_number"],
            "status": execution["status"],
            "verification_status": execution["verification_status"],
            "failure_classification": classification,
            "attempt_count_for_step": attempt_count,
            "can_retry": can_retry,
            "recommended_action": recommended_action
        }
