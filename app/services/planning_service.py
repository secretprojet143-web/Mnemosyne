import json
import re
from typing import List, Dict, Optional

from app.config import settings
from app.db.database import get_connection
from app.services.llm_service import LLMService
from app.services.reasoning_service import ReasoningService


class PlanningService:
    def __init__(self):
        self.llm_service = LLMService()
        self.reasoning_service = ReasoningService()
    # --------------------
    # Plans
    # --------------------
    def create_plan(
        self,
        title: str,
        goal: str = "",
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        reasoning_state_id: Optional[int] = None,
        status: str = "draft"
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO plans (
                conversation_id,
                project_id,
                reasoning_state_id,
                title,
                goal,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            project_id,
            reasoning_state_id,
            title.strip(),
            goal.strip(),
            status
        ))

        plan_id = cur.lastrowid
        conn.commit()
        conn.close()
        return plan_id

    def get_plan_by_id(self, plan_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                project_id,
                reasoning_state_id,
                title,
                goal,
                status,
                created_at,
                updated_at
            FROM plans
            WHERE id = ?
        """, (plan_id,))

        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def list_plans(
        self,
        status: Optional[str] = None,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        reasoning_state_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                id,
                conversation_id,
                project_id,
                reasoning_state_id,
                title,
                goal,
                status,
                created_at,
                updated_at
            FROM plans
        """
        conditions = []
        params = []

        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if conversation_id is not None:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)

        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)

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

    def update_plan(
        self,
        plan_id: int,
        title: Optional[str] = None,
        goal: Optional[str] = None,
        status: Optional[str] = None,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        reasoning_state_id: Optional[int] = None
    ) -> Optional[Dict]:
        existing = self.get_plan_by_id(plan_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE plans
            SET
                conversation_id = ?,
                project_id = ?,
                reasoning_state_id = ?,
                title = ?,
                goal = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            conversation_id if conversation_id is not None else existing["conversation_id"],
            project_id if project_id is not None else existing["project_id"],
            reasoning_state_id if reasoning_state_id is not None else existing["reasoning_state_id"],
            title.strip() if title is not None else existing["title"],
            goal.strip() if goal is not None else existing["goal"],
            status if status is not None else existing["status"],
            plan_id
        ))

        conn.commit()
        conn.close()

        return self.get_plan_by_id(plan_id)

    def plan_exists(self, plan_id: int) -> bool:
        return self.get_plan_by_id(plan_id) is not None

    # --------------------
    # Plan Steps
    # --------------------
    def create_plan_step(
        self,
        plan_id: int,
        step_order: int,
        title: str,
        description: str = "",
        status: str = "pending",
        notes: str = ""
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO plan_steps (
                plan_id,
                step_order,
                title,
                description,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            step_order,
            title.strip(),
            description.strip(),
            status,
            notes.strip()
        ))

        step_id = cur.lastrowid
        conn.commit()
        conn.close()
        return step_id

    def get_plan_step_by_id(self, step_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                plan_id,
                step_order,
                title,
                description,
                status,
                notes,
                created_at,
                updated_at
            FROM plan_steps
            WHERE id = ?
        """, (step_id,))

        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def list_plan_steps(self, plan_id: int) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                plan_id,
                step_order,
                title,
                description,
                status,
                notes,
                created_at,
                updated_at
            FROM plan_steps
            WHERE plan_id = ?
            ORDER BY step_order ASC, id ASC
        """, (plan_id,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_plan_step(
        self,
        step_id: int,
        step_order: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_plan_step_by_id(step_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE plan_steps
            SET
                step_order = ?,
                title = ?,
                description = ?,
                status = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            step_order if step_order is not None else existing["step_order"],
            title.strip() if title is not None else existing["title"],
            description.strip() if description is not None else existing["description"],
            status if status is not None else existing["status"],
            notes.strip() if notes is not None else existing["notes"],
            step_id
        ))

        conn.commit()
        conn.close()

        return self.get_plan_step_by_id(step_id)

    def plan_step_exists(self, step_id: int) -> bool:
        return self.get_plan_step_by_id(step_id) is not None

    # --------------------
    # Step Dependencies
    # --------------------
    def add_step_dependency(
        self,
        plan_id: int,
        step_id: int,
        depends_on_step_id: int
    ) -> Optional[int]:
        if step_id == depends_on_step_id:
            raise ValueError("A step cannot depend on itself.")

        step = self.get_plan_step_by_id(step_id)
        depends_on = self.get_plan_step_by_id(depends_on_step_id)

        if not step or not depends_on:
            return None

        if step["plan_id"] != plan_id or depends_on["plan_id"] != plan_id:
            raise ValueError("Both steps must belong to the specified plan.")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id
            FROM plan_step_dependencies
            WHERE plan_id = ? AND step_id = ? AND depends_on_step_id = ?
            LIMIT 1
        """, (plan_id, step_id, depends_on_step_id))

        existing = cur.fetchone()
        if existing:
            conn.close()
            return existing["id"]

        cur.execute("""
            INSERT INTO plan_step_dependencies (plan_id, step_id, depends_on_step_id)
            VALUES (?, ?, ?)
        """, (plan_id, step_id, depends_on_step_id))

        dep_id = cur.lastrowid
        conn.commit()
        conn.close()

        return dep_id

    def list_step_dependencies(self, plan_id: int) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, plan_id, step_id, depends_on_step_id, created_at
            FROM plan_step_dependencies
            WHERE plan_id = ?
            ORDER BY id ASC
        """, (plan_id,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_step_dependencies(self, step_id: int) -> List[int]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT depends_on_step_id
            FROM plan_step_dependencies
            WHERE step_id = ?
            ORDER BY id ASC
        """, (step_id,))

        rows = cur.fetchall()
        conn.close()

        return [row["depends_on_step_id"] for row in rows]

    def get_blocked_steps(self, plan_id: int) -> List[Dict]:
        steps = self.list_plan_steps(plan_id)
        step_map = {step["id"]: step for step in steps}

        blocked = []

        for step in steps:
            if step["status"] in {"completed", "skipped"}:
                continue

            dependency_ids = self.get_step_dependencies(step["id"])
            if not dependency_ids:
                continue

            unmet = []
            for dep_id in dependency_ids:
                dep_step = step_map.get(dep_id)
                if dep_step and dep_step["status"] not in {"completed", "skipped"}:
                    unmet.append(dep_step)

            if unmet:
                blocked.append({
                    "step": step,
                    "blocked_by": unmet
                })

        return blocked

    def get_ready_steps(self, plan_id: int) -> List[Dict]:
        steps = self.list_plan_steps(plan_id)
        step_map = {step["id"]: step for step in steps}

        ready = []

        for step in steps:
            if step["status"] not in {"pending", "in_progress"}:
                continue

            dependency_ids = self.get_step_dependencies(step["id"])
            if not dependency_ids:
                ready.append(step)
                continue

            all_met = True
            for dep_id in dependency_ids:
                dep_step = step_map.get(dep_id)
                if dep_step and dep_step["status"] not in {"completed", "skipped"}:
                    all_met = False
                    break

            if all_met:
                ready.append(step)

        return ready

    # --------------------
    # Plan Generation from Reasoning
    # --------------------
    def generate_plan_from_reasoning_state(self, reasoning_state_id: int) -> Optional[Dict]:
        reasoning_state = self.reasoning_service.get_reasoning_state_by_id(reasoning_state_id)
        if not reasoning_state:
            return None

        quality = self.reasoning_service.summarize_reasoning_quality(reasoning_state)

        if not quality["validation"]["valid"]:
            raise ValueError("Reasoning state is structurally invalid and cannot be used to generate a plan.")

        prompt = (
            "You are generating a structured execution plan from a reasoning state for Mnemosyne AI.\n"
            "Return ONLY valid JSON.\n\n"
            "Return exactly this structure:\n"
            "{\n"
            '  "title": string,\n'
            '  "goal": string,\n'
            '  "steps": [\n'
            "    {\n"
            '      "step_order": integer,\n'
            '      "title": string,\n'
            '      "description": string,\n'
            '      "status": string,\n'
            '      "notes": string\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- title should be concise and action-oriented.\n"
            "- goal should reflect the reasoning goal.\n"
            "- steps should be concrete and ordered.\n"
            "- step_order should start at 1 and increase by 1.\n"
            "- step status should always be 'pending'.\n"
            "- notes can be empty.\n"
            "- Keep the plan focused and realistic.\n"
            "- Return JSON only."
        )

        reasoning_summary = {
            "task": reasoning_state.get("task"),
            "goal": reasoning_state.get("goal"),
            "constraints": reasoning_state.get("constraints", []),
            "assumptions": reasoning_state.get("assumptions", []),
            "candidate_actions": reasoning_state.get("candidate_actions", []),
            "selected_action": reasoning_state.get("selected_action"),
            "confidence": reasoning_state.get("confidence"),
            "self_check": reasoning_state.get("self_check", {}),
            "quality": quality
        }

        result = self.llm_service.chat(
            model=settings.DEFAULT_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You generate structured plans from reasoning states. Return JSON only."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nReasoning state:\n{json.dumps(reasoning_summary, indent=2)}"
                }
            ],
            temperature=0.2
        )

        raw = result["content"].strip()
        parsed = self._parse_plan_json(raw)
        normalized = self._normalize_generated_plan(parsed)

        plan_id = self.create_plan(
            conversation_id=reasoning_state.get("conversation_id"),
            project_id=reasoning_state.get("project_id"),
            reasoning_state_id=reasoning_state_id,
            title=normalized["title"],
            goal=normalized["goal"],
            status="draft"
        )

        for step in normalized["steps"]:
            self.create_plan_step(
                plan_id=plan_id,
                step_order=step["step_order"],
                title=step["title"],
                description=step["description"],
                status=step["status"],
                notes=step["notes"]
            )

        return {
            "plan": self.get_plan_by_id(plan_id),
            "steps": self.list_plan_steps(plan_id),
            "source_reasoning_state": reasoning_state,
            "reasoning_quality": quality
        }

    def _parse_plan_json(self, raw: str) -> Dict:
        raw = raw.strip()

        try:
            return json.loads(raw)
        except Exception:
            pass

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))

        raise ValueError("Could not parse generated plan JSON.")

    def _normalize_generated_plan(self, data: Dict) -> Dict:
        title = str(data.get("title", "")).strip() or "Generated Plan"
        goal = str(data.get("goal", "")).strip()

        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, list):
            raw_steps = []

        normalized_steps = []

        for idx, step in enumerate(raw_steps, start=1):
            if not isinstance(step, dict):
                continue

            step_order = step.get("step_order", idx)
            try:
                step_order = int(step_order)
            except Exception:
                step_order = idx

            title_value = str(step.get("title", "")).strip()
            if not title_value:
                title_value = f"Step {idx}"

            description = str(step.get("description", "")).strip()
            status = str(step.get("status", "pending")).strip().lower() or "pending"
            if status not in {"pending", "in_progress", "completed", "blocked", "failed", "skipped"}:
                status = "pending"

            notes = str(step.get("notes", "")).strip()

            normalized_steps.append({
                "step_order": step_order,
                "title": title_value,
                "description": description,
                "status": status,
                "notes": notes
            })

        normalized_steps.sort(key=lambda x: x["step_order"])

        for idx, step in enumerate(normalized_steps, start=1):
            step["step_order"] = idx

        return {
            "title": title,
            "goal": goal,
            "steps": normalized_steps
        }

    # --------------------
    # Plan Progress & Health
    # --------------------
    def get_plan_progress_summary(self, plan_id: int) -> Optional[Dict]:
        plan = self.get_plan_by_id(plan_id)
        if not plan:
            return None

        steps = self.list_plan_steps(plan_id)
        blocked = self.get_blocked_steps(plan_id)
        ready = self.get_ready_steps(plan_id)

        total_steps = len(steps)
        completed = sum(1 for s in steps if s["status"] == "completed")
        in_progress = sum(1 for s in steps if s["status"] == "in_progress")
        pending = sum(1 for s in steps if s["status"] == "pending")
        failed = sum(1 for s in steps if s["status"] == "failed")
        skipped = sum(1 for s in steps if s["status"] == "skipped")
        blocked_count = len(blocked)

        percent_complete = round((completed / total_steps) * 100, 2) if total_steps > 0 else 0.0

        return {
            "plan": plan,
            "counts": {
                "total_steps": total_steps,
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending,
                "blocked": blocked_count,
                "failed": failed,
                "skipped": skipped,
                "ready": len(ready)
            },
            "percent_complete": percent_complete,
            "ready_steps": ready,
            "blocked_steps": blocked
        }

    def get_plan_health_summary(self, plan_id: int) -> Optional[Dict]:
        progress = self.get_plan_progress_summary(plan_id)
        if not progress:
            return None

        counts = progress["counts"]
        plan = progress["plan"]

        if counts["total_steps"] == 0:
            health_status = "empty"
            summary = "Plan has no steps yet."
        elif counts["completed"] == counts["total_steps"]:
            health_status = "completed"
            summary = "Plan is fully completed."
        elif counts["failed"] > 0:
            health_status = "at_risk"
            summary = "Plan has failed step(s) and may need intervention."
        elif counts["blocked"] > 0 and counts["ready"] == 0:
            health_status = "blocked"
            summary = "Plan is currently blocked with no ready steps."
        elif counts["blocked"] > 0:
            health_status = "active_with_blockers"
            summary = "Plan is active but some steps are blocked."
        else:
            health_status = "healthy"
            summary = "Plan is progressing without major blockers."

        next_recommended_step = None
        ready_steps = progress["ready_steps"]
        if ready_steps:
            next_recommended_step = ready_steps[0]

        return {
            "plan_id": plan_id,
            "plan_title": plan["title"],
            "plan_status": plan["status"],
            "health_status": health_status,
            "summary": summary,
            "percent_complete": progress["percent_complete"],
            "next_recommended_step": next_recommended_step,
            "counts": counts
        }

    # --------------------
    # Execution-Aware Plan Health
    # --------------------
    def get_plan_execution_health_summary(self, plan_id: int) -> Optional[Dict]:
        from app.services.execution_service import ExecutionService
        execution_service = ExecutionService()

        plan = self.get_plan_by_id(plan_id)
        if not plan:
            return None

        steps = self.list_plan_steps(plan_id)

        recovery_items = []
        failed_execution_count = 0
        retryable_failed_step_count = 0

        for step in steps:
            executions = execution_service.list_step_executions(step_id=step["id"], limit=20)
            if not executions:
                continue

            latest_execution = executions[0]

            if latest_execution["status"] == "failed":
                failed_execution_count += 1
                recovery = execution_service.get_execution_recovery_recommendation(latest_execution["id"])

                if recovery:
                    if recovery["can_retry"]:
                        retryable_failed_step_count += 1

                    recovery_items.append({
                        "step_id": step["id"],
                        "step_title": step["title"],
                        "latest_execution_id": latest_execution["id"],
                        "execution_status": latest_execution["status"],
                        "verification_status": latest_execution["verification_status"],
                        "attempt_count_for_step": recovery["attempt_count_for_step"],
                        "can_retry": recovery["can_retry"],
                        "recommended_action": recovery["recommended_action"],
                        "failure_classification": recovery["failure_classification"]
                    })

        if failed_execution_count == 0:
            execution_health_status = "healthy"
            summary = "No failed executions detected."
        elif retryable_failed_step_count > 0:
            execution_health_status = "retryable_failures"
            summary = "Some failed steps appear retryable."
        else:
            execution_health_status = "requires_intervention"
            summary = "Plan has failed steps that likely need manual intervention."

        next_execution_action = None
        retry_candidates = [item for item in recovery_items if item["can_retry"]]
        if retry_candidates:
            next_execution_action = {
                "type": "retry_step",
                "step_id": retry_candidates[0]["step_id"],
                "step_title": retry_candidates[0]["step_title"],
                "execution_id": retry_candidates[0]["latest_execution_id"]
            }

        return {
            "plan_id": plan_id,
            "plan_title": plan["title"],
            "execution_health_status": execution_health_status,
            "summary": summary,
            "failed_execution_count": failed_execution_count,
            "retryable_failed_step_count": retryable_failed_step_count,
            "recovery_items": recovery_items,
            "next_execution_action": next_execution_action
        }
