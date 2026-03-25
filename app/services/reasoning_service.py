import json
import re
from typing import List, Dict, Optional

from app.config import settings
from app.db.database import get_connection
from app.services.llm_service import LLMService


class ReasoningService:
    def __init__(self):
        self.llm_service = LLMService()

    def create_reasoning_state(
        self,
        task: str,
        goal: str = "",
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        constraints: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
        candidate_actions: Optional[List[str]] = None,
        selected_action: Optional[str] = None,
        confidence: float = 0.5,
        self_check: Optional[Dict] = None,
        status: str = "draft"
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO reasoning_states (
                conversation_id,
                project_id,
                task,
                goal,
                constraints,
                assumptions,
                candidate_actions,
                selected_action,
                confidence,
                self_check,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            project_id,
            task.strip(),
            goal.strip(),
            json.dumps(constraints or []),
            json.dumps(assumptions or []),
            json.dumps(candidate_actions or []),
            selected_action.strip() if selected_action else None,
            confidence,
            json.dumps(self_check or {}),
            status
        ))

        reasoning_id = cur.lastrowid
        conn.commit()
        conn.close()

        return reasoning_id

    def get_reasoning_state_by_id(self, reasoning_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                project_id,
                task,
                goal,
                constraints,
                assumptions,
                candidate_actions,
                selected_action,
                confidence,
                self_check,
                status,
                created_at,
                updated_at
            FROM reasoning_states
            WHERE id = ?
        """, (reasoning_id,))

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return self._decode_reasoning_state(dict(row))

    def list_reasoning_states(
        self,
        status: Optional[str] = None,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                id,
                conversation_id,
                project_id,
                task,
                goal,
                constraints,
                assumptions,
                candidate_actions,
                selected_action,
                confidence,
                self_check,
                status,
                created_at,
                updated_at
            FROM reasoning_states
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

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return [self._decode_reasoning_state(dict(row)) for row in rows]

    def update_reasoning_state(
        self,
        reasoning_id: int,
        task: Optional[str] = None,
        goal: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
        candidate_actions: Optional[List[str]] = None,
        selected_action: Optional[str] = None,
        confidence: Optional[float] = None,
        self_check: Optional[Dict] = None,
        status: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_reasoning_state_by_id(reasoning_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE reasoning_states
            SET
                task = ?,
                goal = ?,
                constraints = ?,
                assumptions = ?,
                candidate_actions = ?,
                selected_action = ?,
                confidence = ?,
                self_check = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            task.strip() if task is not None else existing["task"],
            goal.strip() if goal is not None else existing["goal"],
            json.dumps(constraints) if constraints is not None else json.dumps(existing["constraints"]),
            json.dumps(assumptions) if assumptions is not None else json.dumps(existing["assumptions"]),
            json.dumps(candidate_actions) if candidate_actions is not None else json.dumps(existing["candidate_actions"]),
            selected_action.strip() if selected_action is not None else existing["selected_action"],
            confidence if confidence is not None else existing["confidence"],
            json.dumps(self_check) if self_check is not None else json.dumps(existing["self_check"]),
            status if status is not None else existing["status"],
            reasoning_id
        ))

        conn.commit()
        conn.close()

        return self.get_reasoning_state_by_id(reasoning_id)

    def reasoning_state_exists(self, reasoning_id: int) -> bool:
        return self.get_reasoning_state_by_id(reasoning_id) is not None

    def generate_reasoning_state_from_input(
        self,
        user_input: str,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        context_summary: Optional[str] = None
    ) -> Dict:
        if not user_input.strip():
            raise ValueError("user_input cannot be empty.")

        prompt = (
            "You are generating a structured reasoning state for Mnemosyne AI.\n"
            "Return ONLY valid JSON.\n\n"
            "The reasoning state must contain exactly these fields:\n"
            "{\n"
            '  "task": string,\n'
            '  "goal": string,\n'
            '  "constraints": [string],\n'
            '  "assumptions": [string],\n'
            '  "candidate_actions": [string],\n'
            '  "selected_action": string,\n'
            '  "confidence": number,\n'
            '  "self_check": {\n'
            '    "goal_alignment": boolean,\n'
            '    "constraint_risk": string,\n'
            '    "missing_information": [string]\n'
            "  },\n"
            '  "status": string\n'
            "}\n\n"
            "Rules:\n"
            "- task should describe what the system is trying to reason about.\n"
            "- goal should describe the intended outcome.\n"
            "- constraints should contain important boundaries, limits, or rules.\n"
            "- assumptions should contain current working assumptions.\n"
            "- candidate_actions should contain plausible next actions.\n"
            "- selected_action can be empty if not yet chosen.\n"
            "- confidence must be between 0.0 and 1.0.\n"
            "- self_check.constraint_risk should be one of: low, medium, high.\n"
            "- status should be 'draft'.\n"
            "- Be concrete, concise, and grounded.\n"
            "- Do not return markdown. Do not return explanations. JSON only."
        )

        full_input = f"User input:\n{user_input.strip()}"
        if context_summary:
            full_input += f"\n\nRelevant context:\n{context_summary.strip()}"

        result = self.llm_service.chat(
            model=settings.DEFAULT_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You generate structured reasoning states for a controlled AI system. Return JSON only."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\n{full_input}"
                }
            ],
            temperature=0.2
        )

        raw = result["content"].strip()
        parsed = self._parse_json_response(raw)
        normalized = self._normalize_reasoning_state_payload(parsed)

        reasoning_id = self.create_reasoning_state(
            conversation_id=conversation_id,
            project_id=project_id,
            task=normalized["task"],
            goal=normalized["goal"],
            constraints=normalized["constraints"],
            assumptions=normalized["assumptions"],
            candidate_actions=normalized["candidate_actions"],
            selected_action=normalized["selected_action"],
            confidence=normalized["confidence"],
            self_check=normalized["self_check"],
            status=normalized["status"]
        )

        return self.get_reasoning_state_by_id(reasoning_id)

    def _parse_json_response(self, raw: str) -> Dict:
        raw = raw.strip()

        try:
            return json.loads(raw)
        except Exception:
            pass

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))

        raise ValueError("Could not parse reasoning state JSON.")

    def _normalize_reasoning_state_payload(self, data: Dict) -> Dict:
        def ensure_list(value):
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]
            return []

        def ensure_string(value):
            return str(value).strip() if value is not None else ""

        def ensure_confidence(value):
            try:
                val = float(value)
                return max(0.0, min(1.0, val))
            except Exception:
                return 0.5

        self_check = data.get("self_check", {})
        if not isinstance(self_check, dict):
            self_check = {}

        normalized_self_check = {
            "goal_alignment": bool(self_check.get("goal_alignment", True)),
            "constraint_risk": str(self_check.get("constraint_risk", "medium")).strip().lower() or "medium",
            "missing_information": ensure_list(self_check.get("missing_information"))
        }

        status = str(data.get("status", "draft")).strip().lower() or "draft"
        if status not in {"draft", "active", "completed", "abandoned"}:
            status = "draft"

        return {
            "task": ensure_string(data.get("task")) or "Unspecified reasoning task",
            "goal": ensure_string(data.get("goal")),
            "constraints": ensure_list(data.get("constraints")),
            "assumptions": ensure_list(data.get("assumptions")),
            "candidate_actions": ensure_list(data.get("candidate_actions")),
            "selected_action": ensure_string(data.get("selected_action")),
            "confidence": ensure_confidence(data.get("confidence")),
            "self_check": normalized_self_check,
            "status": status
        }

    def _decode_reasoning_state(self, item: Dict) -> Dict:
        for key in ["constraints", "assumptions", "candidate_actions"]:
            try:
                item[key] = json.loads(item[key]) if item[key] else []
            except Exception:
                item[key] = []

        try:
            item["self_check"] = json.loads(item["self_check"]) if item["self_check"] else {}
        except Exception:
            item["self_check"] = {}

        return item

    def get_relevant_reasoning_states(
        self,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                project_id,
                task,
                goal,
                constraints,
                assumptions,
                candidate_actions,
                selected_action,
                confidence,
                self_check,
                status,
                created_at,
                updated_at
            FROM reasoning_states
            WHERE status IN ('active', 'draft')
            ORDER BY updated_at DESC
            LIMIT 50
        """)

        rows = cur.fetchall()
        conn.close()

        states = [self._decode_reasoning_state(dict(row)) for row in rows]

        scored = []
        for state in states:
            score = 0.0

            if state.get("status") == "active":
                score += 3

            if conversation_id is not None and state.get("conversation_id") == conversation_id:
                score += 3

            if project_id is not None and state.get("project_id") == project_id:
                score += 4

            validation = self.validate_reasoning_payload(state)
            if validation.get("ready_for_action"):
                score += 2

            quality = self.summarize_reasoning_quality(state)
            enriched = dict(state)
            enriched["_quality"] = quality
            scored.append((score, enriched))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def summarize_reasoning_quality(self, state: Dict) -> Dict:
        validation = self.validate_reasoning_payload(state)

        confidence = float(state.get("confidence", 0.5))
        if confidence < 0.4:
            confidence_label = "low"
        elif confidence < 0.75:
            confidence_label = "medium"
        else:
            confidence_label = "high"

        self_check = state.get("self_check") or {}
        missing_information = self_check.get("missing_information", [])
        constraint_risk = str(self_check.get("constraint_risk", "unknown")).strip().lower() or "unknown"

        caution_lines = []

        if confidence_label == "low":
            caution_lines.append("Reasoning confidence is low.")

        if validation["warnings"]:
            caution_lines.append(f"{len(validation['warnings'])} validation warning(s) detected.")

        if missing_information:
            caution_lines.append(f"{len(missing_information)} missing information item(s) identified.")

        if constraint_risk == "high":
            caution_lines.append("Constraint risk is high.")

        if not caution_lines and validation["ready_for_action"]:
            caution_lines.append("Reasoning appears sufficiently grounded and ready for action.")

        return {
            "confidence": confidence,
            "confidence_label": confidence_label,
            "ready_for_action": validation["ready_for_action"],
            "constraint_risk": constraint_risk,
            "warning_count": len(validation["warnings"]),
            "error_count": len(validation["errors"]),
            "missing_information_count": len(missing_information),
            "caution_lines": caution_lines,
            "validation": validation
        }

    def get_reasoning_quality_report(self, reasoning_id: int) -> Optional[Dict]:
        state = self.get_reasoning_state_by_id(reasoning_id)
        if not state:
            return None

        return {
            "reasoning_state_id": reasoning_id,
            "task": state["task"],
            "quality": self.summarize_reasoning_quality(state)
        }

    def validate_reasoning_state(self, reasoning_id: int) -> Optional[Dict]:
        state = self.get_reasoning_state_by_id(reasoning_id)
        if not state:
            return None

        return self.validate_reasoning_payload(state)

    def validate_reasoning_payload(self, state: Dict) -> Dict:
        errors = []
        warnings = []
        quality_flags = []

        task = (state.get("task") or "").strip()
        goal = (state.get("goal") or "").strip()
        constraints = state.get("constraints") or []
        assumptions = state.get("assumptions") or []
        candidate_actions = state.get("candidate_actions") or []
        confidence = float(state.get("confidence", 0.5))
        self_check = state.get("self_check") or {}

        if not task:
            errors.append("Missing task.")

        if not goal:
            warnings.append("Goal is missing or empty.")

        if not isinstance(constraints, list):
            errors.append("Constraints must be a list.")
            constraints = []
        elif len(constraints) == 0:
            warnings.append("No constraints defined.")

        if not isinstance(assumptions, list):
            errors.append("Assumptions must be a list.")
            assumptions = []
        elif len(assumptions) == 0:
            warnings.append("No assumptions recorded.")

        if not isinstance(candidate_actions, list):
            errors.append("Candidate actions must be a list.")
            candidate_actions = []
        elif len(candidate_actions) == 0:
            warnings.append("No candidate actions proposed.")

        if confidence < 0.0 or confidence > 1.0:
            errors.append("Confidence is outside valid range 0.0-1.0.")
        elif confidence < 0.4:
            warnings.append("Confidence is low.")
            quality_flags.append("low_confidence")
        elif confidence > 0.9 and (len(constraints) == 0 or len(assumptions) == 0):
            warnings.append("Confidence may be too high for a weakly grounded reasoning state.")
            quality_flags.append("overconfident")

        if not isinstance(self_check, dict):
            errors.append("self_check must be an object.")
            self_check = {}

        goal_alignment = self_check.get("goal_alignment")
        constraint_risk = str(self_check.get("constraint_risk", "")).strip().lower()
        missing_information = self_check.get("missing_information", [])

        if goal_alignment is None:
            warnings.append("self_check.goal_alignment is missing.")

        if constraint_risk not in {"low", "medium", "high"}:
            warnings.append("self_check.constraint_risk is missing or invalid.")

        if not isinstance(missing_information, list):
            warnings.append("self_check.missing_information should be a list.")

        if constraint_risk == "high":
            quality_flags.append("high_constraint_risk")

        if len(constraints) > 0:
            quality_flags.append("has_constraints")

        if len(assumptions) > 0:
            quality_flags.append("has_assumptions")

        if len(candidate_actions) > 0:
            quality_flags.append("has_candidate_actions")

        ready_for_action = (
            len(errors) == 0
            and len(candidate_actions) > 0
            and len(constraints) > 0
            and confidence >= 0.4
            and constraint_risk in {"low", "medium"}
        )

        return {
            "valid": len(errors) == 0,
            "ready_for_action": ready_for_action,
            "errors": errors,
            "warnings": warnings,
            "quality_flags": quality_flags,
            "summary": {
                "task_present": bool(task),
                "goal_present": bool(goal),
                "constraint_count": len(constraints),
                "assumption_count": len(assumptions),
                "candidate_action_count": len(candidate_actions),
                "confidence": confidence,
                "constraint_risk": constraint_risk or None
            }
        }
