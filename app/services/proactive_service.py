from typing import Dict, List

from app.services.continuity_service import ContinuityService
from app.services.temporal_service import TemporalService
from app.services.recommendation_service import RecommendationService


class ProactiveService:
    def __init__(self):
        self.continuity_service = ContinuityService()
        self.temporal_service = TemporalService()
        self.recommendation_service = RecommendationService()

    def generate_proactive_briefing(self) -> Dict:
        next_actions = self.continuity_service.suggest_next_actions(limit=8)
        reconfirmation_candidates = self.temporal_service.get_reconfirmation_candidates(stale_after_days=30)[:5]
        aging_goals = self.temporal_service.detect_aging_goals(stale_after_days=21)[:5]
        aging_open_loops = self.temporal_service.detect_aging_open_loops(stale_after_days=14)[:5]
        top_pending_memory = self.recommendation_service.get_top_pending_recommendations(limit=5, min_score=0.9)

        top_priorities = self._build_top_priorities(
            next_actions=next_actions,
            aging_goals=aging_goals,
            aging_open_loops=aging_open_loops
        )

        stalled_items = self._build_stalled_items(
            aging_goals=aging_goals,
            aging_open_loops=aging_open_loops
        )

        briefing_lines = self._build_briefing_lines(
            top_priorities=top_priorities,
            reconfirmation_candidates=reconfirmation_candidates,
            stalled_items=stalled_items,
            pending_memory_items=top_pending_memory.get("items", [])
        )

        return {
            "summary_counts": {
                "next_actions": len(next_actions),
                "reconfirmation_candidates": len(reconfirmation_candidates),
                "aging_goals": len(aging_goals),
                "aging_open_loops": len(aging_open_loops),
                "pending_memory_recommendations": top_pending_memory.get("count", 0)
            },
            "top_priorities": top_priorities,
            "reconfirmation_needs": reconfirmation_candidates,
            "stalled_items": stalled_items,
            "memory_review_queue": top_pending_memory.get("items", []),
            "briefing_lines": briefing_lines
        }

    def _build_top_priorities(
        self,
        next_actions: List[Dict],
        aging_goals: List[Dict],
        aging_open_loops: List[Dict]
    ) -> List[Dict]:
        priorities = []

        for item in next_actions[:5]:
            priorities.append({
                "type": item["type"],
                "text": item["text"],
                "priority": item["priority"],
                "score": item["score"],
                "source": "next_action"
            })

        for item in aging_open_loops[:3]:
            priorities.append({
                "type": "aging_open_loop",
                "text": item["description"],
                "priority": item["priority"],
                "score": item["age_days"] + 2,
                "source": "temporal_health"
            })

        for item in aging_goals[:3]:
            priorities.append({
                "type": "aging_goal",
                "text": item["goal_text"],
                "priority": item["priority"],
                "score": item["age_days"] + 1,
                "source": "temporal_health"
            })

        seen = set()
        deduped = []
        for item in priorities:
            key = item["text"].strip().lower()
            if key not in seen:
                seen.add(key)
                deduped.append(item)

        deduped.sort(key=lambda x: x["score"], reverse=True)
        return deduped[:8]

    def _build_stalled_items(
        self,
        aging_goals: List[Dict],
        aging_open_loops: List[Dict]
    ) -> List[Dict]:
        stalled = []

        for item in aging_open_loops:
            stalled.append({
                "type": "open_loop",
                "text": item["description"],
                "age_days": item["age_days"],
                "priority": item["priority"]
            })

        for item in aging_goals:
            stalled.append({
                "type": "goal",
                "text": item["goal_text"],
                "age_days": item["age_days"],
                "priority": item["priority"]
            })

        stalled.sort(key=lambda x: x["age_days"], reverse=True)
        return stalled[:10]

    def _build_briefing_lines(
        self,
        top_priorities: List[Dict],
        reconfirmation_candidates: List[Dict],
        stalled_items: List[Dict],
        pending_memory_items: List[Dict]
    ) -> List[str]:
        lines = []

        if top_priorities:
            lines.append(f"Top active priority: {top_priorities[0]['text']}")

        if stalled_items:
            lines.append(f"{len(stalled_items)} item(s) may be stalled or aging and could need attention.")

        if reconfirmation_candidates:
            lines.append(
                f"{len(reconfirmation_candidates)} memory item(s) may need reconfirmation."
            )

        if pending_memory_items:
            lines.append(
                f"{len(pending_memory_items)} strong memory recommendation(s) are awaiting review."
            )

        if not lines:
            lines.append("No major proactive signals detected right now.")

        return lines
