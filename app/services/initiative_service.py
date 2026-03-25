from typing import Dict, List, Optional

from app.db.database import get_connection
from app.services.proactive_service import ProactiveService


class InitiativeService:
    def __init__(self):
        self.proactive_service = ProactiveService()

    def get_suggestions_for_chat(
        self,
        conversation_id: Optional[int] = None,
        max_items: Optional[int] = None,
        initiative_mode: str = "balanced"
    ) -> Dict:
        policy = self._get_initiative_policy(initiative_mode)
        effective_max_items = max_items if max_items is not None else policy["max_items"]
        allowed_types = policy["allowed_types"]
        cooldown_limit = policy["cooldown_limit"]

        briefing = self.proactive_service.generate_proactive_briefing()

        candidates = []

        top_priorities = briefing.get("top_priorities", [])
        reconfirmation_needs = briefing.get("reconfirmation_needs", [])
        stalled_items = briefing.get("stalled_items", [])
        memory_review_queue = briefing.get("memory_review_queue", [])

        if top_priorities:
            top = top_priorities[0]
            candidates.append({
                "suggestion_type": "top_priority",
                "suggestion_text": f"Top active priority: {top['text']}",
                "payload": top
            })

        if stalled_items:
            stalled = stalled_items[0]
            candidates.append({
                "suggestion_type": "stalled_item",
                "suggestion_text": f"Possible stalled item: {stalled['text']}",
                "payload": stalled
            })

        if reconfirmation_needs:
            item = reconfirmation_needs[0]
            candidates.append({
                "suggestion_type": "reconfirmation",
                "suggestion_text": f"Memory may need reconfirmation: {item['fact_text']}",
                "payload": item
            })

        if memory_review_queue:
            item = memory_review_queue[0]
            candidates.append({
                "suggestion_type": "memory_review",
                "suggestion_text": f"Strong memory recommendation awaiting review: {item['recommendation_text']}",
                "payload": item
            })

        candidates = [c for c in candidates if c["suggestion_type"] in allowed_types]

        surfaced = []
        skipped = []

        for candidate in candidates:
            if len(surfaced) >= effective_max_items:
                break

            if self.should_surface(
                candidate["suggestion_type"],
                candidate["suggestion_text"],
                cooldown_limit=cooldown_limit
            ):
                self.record_surface_event(
                    suggestion_type=candidate["suggestion_type"],
                    suggestion_text=candidate["suggestion_text"],
                    conversation_id=conversation_id
                )
                surfaced.append(candidate)
            else:
                skipped.append({
                    "suggestion_type": candidate["suggestion_type"],
                    "suggestion_text": candidate["suggestion_text"],
                    "reason": "cooldown_active"
                })

        return {
            "initiative_mode": initiative_mode,
            "policy": {
                "max_items": effective_max_items,
                "cooldown_limit": cooldown_limit,
                "allowed_types": sorted(allowed_types)
            },
            "surfaced_count": len(surfaced),
            "surfaced": surfaced,
            "skipped": skipped
        }

    def _get_initiative_policy(self, initiative_mode: str) -> Dict:
        policies = {
            "quiet": {
                "max_items": 1,
                "cooldown_limit": 6,
                "allowed_types": {"top_priority"}
            },
            "balanced": {
                "max_items": 2,
                "cooldown_limit": 3,
                "allowed_types": {"top_priority", "stalled_item", "reconfirmation", "memory_review"}
            },
            "active": {
                "max_items": 3,
                "cooldown_limit": 2,
                "allowed_types": {"top_priority", "stalled_item", "reconfirmation", "memory_review"}
            },
            "coach": {
                "max_items": 4,
                "cooldown_limit": 1,
                "allowed_types": {"top_priority", "stalled_item", "reconfirmation", "memory_review"}
            }
        }
        return policies.get(initiative_mode, policies["balanced"])

    def should_surface(self, suggestion_type: str, suggestion_text: str, cooldown_limit: int = 3) -> bool:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT suggestion_type, suggestion_text
            FROM surfaced_suggestions
            ORDER BY id DESC
            LIMIT ?
        """, (cooldown_limit,))

        rows = cur.fetchall()
        conn.close()

        norm_type = suggestion_type.strip().lower()
        norm_text = suggestion_text.strip().lower()

        for row in rows:
            if (
                row["suggestion_type"].strip().lower() == norm_type
                and row["suggestion_text"].strip().lower() == norm_text
            ):
                return False

        return True

    def record_surface_event(
        self,
        suggestion_type: str,
        suggestion_text: str,
        conversation_id: Optional[int] = None
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO surfaced_suggestions (suggestion_type, suggestion_text, conversation_id)
            VALUES (?, ?, ?)
        """, (suggestion_type, suggestion_text, conversation_id))

        suggestion_id = cur.lastrowid
        conn.commit()
        conn.close()

        return suggestion_id

    def list_recent_surface_events(self, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, suggestion_type, suggestion_text, conversation_id, surfaced_at
            FROM surfaced_suggestions
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]
