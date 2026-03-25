from datetime import datetime
from typing import Dict, List, Optional

from app.services.memory_service import MemoryService
from app.services.continuity_service import ContinuityService


class TemporalService:
    def __init__(self):
        self.memory_service = MemoryService()
        self.continuity_service = ContinuityService()

    def get_current_vs_previous(self, kind: str) -> Dict:
        timeline = self.memory_service.get_fact_timeline_by_kind(kind)

        if not timeline:
            return {
                "kind": kind,
                "has_change": False,
                "current": None,
                "previous": None,
                "timeline_length": 0
            }

        active_items = [item for item in timeline if item.get("status") == "active"]
        historical_items = [item for item in timeline if item.get("status") in {"superseded", "outdated"}]

        current = active_items[-1] if active_items else timeline[-1]
        previous = historical_items[-1] if historical_items else (timeline[-2] if len(timeline) > 1 else None)

        has_change = False
        if previous and current:
            has_change = previous.get("parsed_value") != current.get("parsed_value")

        return {
            "kind": kind,
            "has_change": has_change,
            "current": current,
            "previous": previous,
            "timeline_length": len(timeline)
        }

    def detect_changes_for_kind(self, kind: str) -> Dict:
        snapshot = self.get_current_vs_previous(kind)

        current = snapshot.get("current")
        previous = snapshot.get("previous")
        has_change = snapshot.get("has_change", False)

        if not current:
            return {
                "kind": kind,
                "has_change": False,
                "summary": None,
                "current_value": None,
                "previous_value": None,
                "timeline_length": 0
            }

        current_value = current.get("parsed_value")
        previous_value = previous.get("parsed_value") if previous else None

        summary = None
        if has_change and previous_value and current_value:
            summary = self._build_change_summary(kind, previous_value, current_value)
        elif current_value:
            summary = self._build_current_state_summary(kind, current_value)

        return {
            "kind": kind,
            "has_change": has_change,
            "summary": summary,
            "current_value": current_value,
            "previous_value": previous_value,
            "timeline_length": snapshot.get("timeline_length", 0),
            "current": current,
            "previous": previous
        }

    def detect_all_changes(self) -> Dict[str, Dict]:
        supported_kinds = ["name", "location_live", "work_role", "work_company"]

        results = {}
        for kind in supported_kinds:
            results[kind] = self.detect_changes_for_kind(kind)

        return results

    def _build_change_summary(self, kind: str, previous_value: str, current_value: str) -> str:
        templates = {
            "name": f"User's name changed from {previous_value} to {current_value}.",
            "location_live": f"User's location changed from {previous_value} to {current_value}.",
            "work_role": f"User's work role changed from {previous_value} to {current_value}.",
            "work_company": f"User's workplace changed from {previous_value} to {current_value}.",
        }
        return templates.get(kind, f"{kind} changed from {previous_value} to {current_value}.")

    def _build_current_state_summary(self, kind: str, current_value: str) -> str:
        templates = {
            "name": f"User's current known name is {current_value}.",
            "location_live": f"User's current known location is {current_value}.",
            "work_role": f"User's current known work role is {current_value}.",
            "work_company": f"User's current known workplace is {current_value}.",
        }
        return templates.get(kind, f"Current known {kind} is {current_value}.")

    def _parse_dt(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", ""))
        except Exception:
            return None

    def _days_old(self, value: Optional[str]) -> Optional[int]:
        dt = self._parse_dt(value)
        if not dt:
            return None

        now = datetime.now()
        delta = now - dt
        return max(delta.days, 0)

    def detect_stale_facts(self, stale_after_days: int = 30) -> List[Dict]:
        facts = self.memory_service.get_active_facts()
        stale = []

        for fact in facts:
            age_days = self._days_old(
                fact.get("last_confirmed_at") or fact.get("updated_at") or fact.get("created_at")
            )
            if age_days is not None and age_days >= stale_after_days:
                stale.append({
                    "fact_id": fact["id"],
                    "fact_text": fact["fact_text"],
                    "category": fact["category"],
                    "age_days": age_days,
                    "last_confirmed_at": fact.get("last_confirmed_at"),
                    "status": "stale_fact"
                })

        stale.sort(key=lambda x: x["age_days"], reverse=True)
        return stale

    def detect_aging_open_loops(self, stale_after_days: int = 14) -> List[Dict]:
        loops = self.continuity_service.list_open_loops(status="open")
        aging = []

        for loop in loops:
            age_days = self._days_old(loop.get("updated_at") or loop.get("created_at"))
            if age_days is not None and age_days >= stale_after_days:
                aging.append({
                    "open_loop_id": loop["id"],
                    "description": loop["description"],
                    "priority": loop["priority"],
                    "project_id": loop.get("project_id"),
                    "conversation_id": loop.get("conversation_id"),
                    "age_days": age_days,
                    "status": "aging_open_loop"
                })

        aging.sort(key=lambda x: (x["age_days"], x["priority"]), reverse=True)
        return aging

    def detect_aging_goals(self, stale_after_days: int = 21) -> List[Dict]:
        goals = self.continuity_service.list_goals(status="active")
        aging = []

        for goal in goals:
            age_days = self._days_old(goal.get("updated_at") or goal.get("created_at"))
            if age_days is not None and age_days >= stale_after_days:
                aging.append({
                    "goal_id": goal["id"],
                    "goal_text": goal["goal_text"],
                    "priority": goal["priority"],
                    "project_id": goal.get("project_id"),
                    "age_days": age_days,
                    "status": "aging_goal"
                })

        aging.sort(key=lambda x: (x["age_days"], x["priority"]), reverse=True)
        return aging

    def detect_recurring_open_loop_patterns(self) -> List[Dict]:
        loops = self.continuity_service.list_open_loops()
        grouped = {}

        for loop in loops:
            text = " ".join(loop["description"].strip().lower().split())
            if not text:
                continue

            grouped.setdefault(text, []).append(loop)

        recurring = []
        for text, items in grouped.items():
            if len(items) >= 2:
                recurring.append({
                    "normalized_description": text,
                    "occurrence_count": len(items),
                    "open_loop_ids": [item["id"] for item in items],
                    "statuses": sorted(set(item["status"] for item in items)),
                    "latest_updated_at": max(
                        item.get("updated_at") or item.get("created_at") for item in items
                    )
                })

        recurring.sort(key=lambda x: x["occurrence_count"], reverse=True)
        return recurring

    def get_temporal_health_report(self) -> Dict:
        stale_facts = self.detect_stale_facts()
        aging_open_loops = self.detect_aging_open_loops()
        aging_goals = self.detect_aging_goals()
        recurring_open_loops = self.detect_recurring_open_loop_patterns()

        return {
            "counts": {
                "stale_facts": len(stale_facts),
                "aging_open_loops": len(aging_open_loops),
                "aging_goals": len(aging_goals),
                "recurring_open_loop_patterns": len(recurring_open_loops)
            },
            "stale_facts": stale_facts[:20],
            "aging_open_loops": aging_open_loops[:20],
            "aging_goals": aging_goals[:20],
            "recurring_open_loop_patterns": recurring_open_loops[:20]
        }

    def get_reconfirmation_candidates(self, stale_after_days: int = 30) -> List[Dict]:
        stale_facts = self.detect_stale_facts(stale_after_days=stale_after_days)

        candidates = []
        for fact in stale_facts:
            priority_score = 0

            if fact["category"] in {"identity", "location", "work"}:
                priority_score += 2
            else:
                priority_score += 1

            full_fact = self.memory_service.get_fact_by_id(fact["fact_id"])
            if full_fact:
                if full_fact.get("is_pinned"):
                    priority_score += 2
                confidence = float(full_fact.get("confidence", 0.0))
                if confidence >= 0.9:
                    priority_score += 1

            candidates.append({
                "fact_id": fact["fact_id"],
                "fact_text": fact["fact_text"],
                "category": fact["category"],
                "age_days": fact["age_days"],
                "priority_score": priority_score,
                "reason": "important active fact has not been reconfirmed recently"
            })

        candidates.sort(
            key=lambda x: (x["priority_score"], x["age_days"]),
            reverse=True
        )
        return candidates
