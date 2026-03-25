from typing import List, Dict, Optional

from app.db.database import get_connection
from app.services.evolution_service import EvolutionService
from app.services.memory_service import MemoryService
from app.services.continuity_service import ContinuityService


class RecommendationService:
    def __init__(self):
        self.evolution_service = EvolutionService()
        self.memory_service = MemoryService()
        self.continuity_service = ContinuityService()

    def list_recommendations(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT id, source_type, source_ref_id, recommendation_text, category, confidence, status, decision_note, created_at, updated_at
            FROM memory_recommendations
        """
        conditions = []
        params = []

        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if category is not None:
            conditions.append("category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY confidence DESC, id DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_recommendation_by_id(self, recommendation_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, source_type, source_ref_id, recommendation_text, category, confidence, status, decision_note, created_at, updated_at
            FROM memory_recommendations
            WHERE id = ?
        """, (recommendation_id,))

        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def recommendation_exists(
        self,
        recommendation_text: str,
        source_type: str,
        source_ref_id: Optional[int]
    ) -> bool:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id
            FROM memory_recommendations
            WHERE LOWER(recommendation_text) = LOWER(?)
              AND source_type = ?
              AND (
                    source_ref_id = ?
                    OR (source_ref_id IS NULL AND ? IS NULL)
                  )
            LIMIT 1
        """, (recommendation_text.strip(), source_type, source_ref_id, source_ref_id))

        row = cur.fetchone()
        conn.close()

        return row is not None

    def create_recommendation(
        self,
        source_type: str,
        source_ref_id: Optional[int],
        recommendation_text: str,
        category: str = "memory_candidate",
        confidence: float = 0.75,
        status: str = "proposed"
    ) -> Optional[int]:
        recommendation_text = recommendation_text.strip()
        if not recommendation_text:
            return None

        if self.recommendation_exists(recommendation_text, source_type, source_ref_id):
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO memory_recommendations (
                source_type,
                source_ref_id,
                recommendation_text,
                category,
                confidence,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            source_type,
            source_ref_id,
            recommendation_text,
            category,
            confidence,
            status
        ))

        recommendation_id = cur.lastrowid
        conn.commit()
        conn.close()

        return recommendation_id

    def generate_from_reflections(self, limit: int = 20) -> Dict:
        reflections = self.evolution_service.get_recent_reflections(limit=limit)

        created = []
        skipped = []

        for reflection in reflections:
            reflection_id = reflection["id"]

            for item in reflection.get("recommended_long_term_memories", []):
                rec_id = self.create_recommendation(
                    source_type="reflection",
                    source_ref_id=reflection_id,
                    recommendation_text=item,
                    category="memory_candidate",
                    confidence=0.85,
                    status="proposed"
                )
                if rec_id:
                    created.append(self.get_recommendation_by_id(rec_id))
                else:
                    skipped.append({
                        "source_type": "reflection",
                        "source_ref_id": reflection_id,
                        "recommendation_text": item,
                        "reason": "duplicate_or_invalid"
                    })

            for item in reflection.get("user_insights", []):
                rec_id = self.create_recommendation(
                    source_type="reflection",
                    source_ref_id=reflection_id,
                    recommendation_text=item,
                    category="user_insight",
                    confidence=0.78,
                    status="proposed"
                )
                if rec_id:
                    created.append(self.get_recommendation_by_id(rec_id))
                else:
                    skipped.append({
                        "source_type": "reflection",
                        "source_ref_id": reflection_id,
                        "recommendation_text": item,
                        "reason": "duplicate_or_invalid"
                    })

            for item in reflection.get("preference_updates", []):
                rec_id = self.create_recommendation(
                    source_type="reflection",
                    source_ref_id=reflection_id,
                    recommendation_text=item,
                    category="preference",
                    confidence=0.80,
                    status="proposed"
                )
                if rec_id:
                    created.append(self.get_recommendation_by_id(rec_id))
                else:
                    skipped.append({
                        "source_type": "reflection",
                        "source_ref_id": reflection_id,
                        "recommendation_text": item,
                        "reason": "duplicate_or_invalid"
                    })

        return {
            "success": True,
            "reflections_scanned": len(reflections),
            "created_count": len(created),
            "skipped_count": len(skipped),
            "created": created,
            "skipped": skipped[:20]
        }

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.strip().lower().split())

    def aggregate_recommendations(
        self,
        status: str = "proposed",
        limit: int = 100
    ) -> List[Dict]:
        recommendations = self.list_recommendations(status=status, limit=1000)

        grouped = {}

        for rec in recommendations:
            normalized_text = self._normalize_text(rec["recommendation_text"])
            key = (normalized_text, rec["category"])

            if key not in grouped:
                grouped[key] = {
                    "recommendation_text": rec["recommendation_text"],
                    "normalized_text": normalized_text,
                    "category": rec["category"],
                    "occurrence_count": 0,
                    "average_confidence": 0.0,
                    "source_types": set(),
                    "source_refs": [],
                    "recommendation_ids": [],
                    "latest_created_at": rec["created_at"]
                }

            grouped[key]["occurrence_count"] += 1
            grouped[key]["average_confidence"] += float(rec.get("confidence", 0.0))
            grouped[key]["source_types"].add(rec["source_type"])
            grouped[key]["source_refs"].append({
                "source_type": rec["source_type"],
                "source_ref_id": rec["source_ref_id"]
            })
            grouped[key]["recommendation_ids"].append(rec["id"])

            if rec["created_at"] > grouped[key]["latest_created_at"]:
                grouped[key]["latest_created_at"] = rec["created_at"]

        aggregated = []

        for _, group in grouped.items():
            count = group["occurrence_count"]
            avg_conf = group["average_confidence"] / count if count else 0.0
            distinct_source_types = len(group["source_types"])

            recurrence_bonus = min(0.4, 0.08 * (count - 1)) if count > 1 else 0.0
            source_diversity_bonus = 0.1 * (distinct_source_types - 1) if distinct_source_types > 1 else 0.0

            score = avg_conf + recurrence_bonus + source_diversity_bonus

            aggregated.append({
                "recommendation_text": group["recommendation_text"],
                "category": group["category"],
                "occurrence_count": count,
                "average_confidence": round(avg_conf, 4),
                "distinct_source_types": distinct_source_types,
                "source_types": sorted(group["source_types"]),
                "source_refs": group["source_refs"],
                "recommendation_ids": group["recommendation_ids"],
                "latest_created_at": group["latest_created_at"],
                "score": round(score, 4),
                "scoring": {
                    "average_confidence": round(avg_conf, 4),
                    "recurrence_bonus": round(recurrence_bonus, 4),
                    "source_diversity_bonus": round(source_diversity_bonus, 4)
                }
            })

        aggregated.sort(
            key=lambda x: (
                x["score"],
                x["occurrence_count"],
                x["latest_created_at"]
            ),
            reverse=True
        )

        return aggregated[:limit]

    def get_top_candidates(
        self,
        status: str = "proposed",
        limit: int = 20
    ) -> Dict:
        aggregated = self.aggregate_recommendations(status=status, limit=limit)

        return {
            "status": status,
            "candidate_count": len(aggregated),
            "candidates": aggregated
        }

    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        allowed = {
            "proposed": {"accepted", "rejected", "promoted"},
            "accepted": {"rejected", "promoted"},
            "rejected": set(),
            "promoted": set()
        }
        return new_status == current_status or new_status in allowed.get(current_status, set())

    def update_recommendation_status(
        self,
        recommendation_id: int,
        new_status: str,
        decision_note: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_recommendation_by_id(recommendation_id)
        if not existing:
            return None

        current_status = existing["status"]
        if not self._is_valid_status_transition(current_status, new_status):
            raise ValueError(f"Invalid status transition: {current_status} -> {new_status}")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE memory_recommendations
            SET
                status = ?,
                decision_note = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            new_status,
            decision_note.strip() if decision_note else existing.get("decision_note"),
            recommendation_id
        ))

        conn.commit()
        conn.close()

        return self.get_recommendation_by_id(recommendation_id)

    def accept_recommendation(self, recommendation_id: int, decision_note: Optional[str] = None) -> Optional[Dict]:
        return self.update_recommendation_status(
            recommendation_id=recommendation_id,
            new_status="accepted",
            decision_note=decision_note
        )

    def reject_recommendation(self, recommendation_id: int, decision_note: Optional[str] = None) -> Optional[Dict]:
        return self.update_recommendation_status(
            recommendation_id=recommendation_id,
            new_status="rejected",
            decision_note=decision_note
        )

    def _map_recommendation_category_to_fact_category(self, category: str) -> Optional[str]:
        mapping = {
            "user_insight": "identity",
            "preference": "preference",
            "memory_candidate": "general",
            "project": "work",
            "goal": "general"
        }
        return mapping.get(category)

    def promote_recommendation_to_fact(
        self,
        recommendation_id: int,
        pin: bool = True
    ) -> Optional[Dict]:
        recommendation = self.get_recommendation_by_id(recommendation_id)
        if not recommendation:
            return None

        if recommendation["status"] != "accepted":
            raise ValueError("Only accepted recommendations can be promoted.")

        fact_category = self._map_recommendation_category_to_fact_category(recommendation["category"])
        if not fact_category:
            raise ValueError(f"Recommendation category '{recommendation['category']}' cannot be promoted to a fact.")

        recommendation_text = recommendation["recommendation_text"].strip()
        if not recommendation_text:
            raise ValueError("Recommendation text is empty.")

        existing_facts = self.memory_service.get_all_facts()
        for fact in existing_facts:
            if (
                fact.get("status") == "active"
                and fact.get("fact_text", "").strip().lower() == recommendation_text.lower()
            ):
                updated_recommendation = self.update_recommendation_status(
                    recommendation_id=recommendation_id,
                    new_status="promoted",
                    decision_note="Matched existing active fact; marked as promoted."
                )
                return {
                    "recommendation": updated_recommendation,
                    "fact": fact,
                    "action": "matched_existing_fact"
                }

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO facts (
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            None,
            None,
            recommendation_text,
            fact_category,
            recommendation.get("confidence", 0.8),
            "active",
            "personal",
            1 if pin else 0,
            "corrected"
        ))

        fact_id = cur.lastrowid
        conn.commit()
        conn.close()

        updated_recommendation = self.update_recommendation_status(
            recommendation_id=recommendation_id,
            new_status="promoted",
            decision_note="Promoted into durable fact memory."
        )

        fact = self.memory_service.get_fact_by_id(fact_id)

        return {
            "recommendation": updated_recommendation,
            "fact": fact,
            "action": "created_fact"
        }

    def promote_recommendation_to_goal(
        self,
        recommendation_id: int,
        project_id: Optional[int] = None,
        priority: str = "high"
    ) -> Optional[Dict]:
        recommendation = self.get_recommendation_by_id(recommendation_id)
        if not recommendation:
            return None

        if recommendation["status"] != "accepted":
            raise ValueError("Only accepted recommendations can be promoted.")

        goal_text = recommendation["recommendation_text"].strip()
        if not goal_text:
            raise ValueError("Recommendation text is empty.")

        existing_goal = self.continuity_service.find_similar_goal(goal_text)
        if existing_goal:
            updated_recommendation = self.update_recommendation_status(
                recommendation_id=recommendation_id,
                new_status="promoted",
                decision_note="Matched existing active goal; marked as promoted."
            )
            return {
                "recommendation": updated_recommendation,
                "goal": existing_goal,
                "action": "matched_existing_goal"
            }

        goal_id = self.continuity_service.create_goal(
            goal_text=goal_text,
            project_id=project_id,
            status="active",
            priority=priority
        )

        updated_recommendation = self.update_recommendation_status(
            recommendation_id=recommendation_id,
            new_status="promoted",
            decision_note="Promoted into active goal."
        )

        goal = self.continuity_service.get_goal_by_id(goal_id)

        return {
            "recommendation": updated_recommendation,
            "goal": goal,
            "action": "created_goal"
        }

    def promote_recommendation_to_open_loop(
        self,
        recommendation_id: int,
        project_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        priority: str = "high"
    ) -> Optional[Dict]:
        recommendation = self.get_recommendation_by_id(recommendation_id)
        if not recommendation:
            return None

        if recommendation["status"] != "accepted":
            raise ValueError("Only accepted recommendations can be promoted.")

        description = recommendation["recommendation_text"].strip()
        if not description:
            raise ValueError("Recommendation text is empty.")

        existing_loop = self.continuity_service.find_similar_open_loop(description)
        if existing_loop:
            updated_recommendation = self.update_recommendation_status(
                recommendation_id=recommendation_id,
                new_status="promoted",
                decision_note="Matched existing open loop; marked as promoted."
            )
            return {
                "recommendation": updated_recommendation,
                "open_loop": existing_loop,
                "action": "matched_existing_open_loop"
            }

        loop_id = self.continuity_service.create_open_loop(
            description=description,
            project_id=project_id,
            conversation_id=conversation_id,
            status="open",
            priority=priority
        )

        updated_recommendation = self.update_recommendation_status(
            recommendation_id=recommendation_id,
            new_status="promoted",
            decision_note="Promoted into active open loop."
        )

        open_loop = self.continuity_service.get_open_loop_by_id(loop_id)

        return {
            "recommendation": updated_recommendation,
            "open_loop": open_loop,
            "action": "created_open_loop"
        }

    def get_review_queue(self, limit: int = 25) -> Dict:
        candidates = self.get_top_candidates(status="proposed", limit=limit)

        return {
            "queue_size": candidates["candidate_count"],
            "items": candidates["candidates"]
        }

    def get_top_pending_recommendations(self, limit: int = 5, min_score: float = 0.9) -> Dict:
        candidates = self.get_top_candidates(status="proposed", limit=100)["candidates"]

        filtered = [c for c in candidates if c.get("score", 0.0) >= min_score]

        return {
            "min_score": min_score,
            "count": min(len(filtered), limit),
            "items": filtered[:limit]
        }
