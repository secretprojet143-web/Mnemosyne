from datetime import date, datetime
from typing import List, Dict, Optional

from app.config import settings
from app.db.database import get_connection
from app.services.memory_service import MemoryService
from app.services.evolution_service import EvolutionService
from app.services.semantic_memory_service import SemanticMemoryService


class ConsolidationService:
    """
    Automatic memory consolidation and background evolution.
    
    Handles:
    - Auto-creating episodes after message threshold
    - Auto-generating daily learnings
    - Consolidating duplicate facts
    - Prioritizing important memories
    """

    def __init__(self):
        self.memory_service = MemoryService()
        self.evolution_service = EvolutionService()
        self.semantic_memory_service = SemanticMemoryService()

    def check_and_consolidate_conversation(self, conversation_id: int) -> Dict:
        """
        Check if a conversation needs consolidation and perform it.
        Triggered after each chat message.
        """
        messages = self.memory_service.get_conversation_messages(conversation_id)
        message_count = len(messages)

        results = {
            "episode_created": False,
            "facts_consolidated": False,
            "message_count": message_count
        }

        episode_threshold = 10
        existing_episodes = self._get_conversation_episode_count(conversation_id)

        if message_count >= episode_threshold and existing_episodes == 0:
            episode_result = self.evolution_service.create_episode_for_conversation(conversation_id)
            if episode_result.get("success"):
                results["episode_created"] = True
                results["episode_id"] = episode_result.get("episodic_memory_id")

        if message_count % 20 == 0 and message_count > 0:
            consolidated = self.consolidate_facts()
            results["facts_consolidated"] = consolidated > 0
            results["facts_removed"] = consolidated

        return results

    def consolidate_facts(self) -> int:
        """
        Consolidate duplicate active facts in a non-destructive way.
        Keeps the strongest fact active and marks weaker duplicates as superseded.
        Returns number of facts consolidated.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                fact_text,
                category,
                confidence,
                status,
                is_pinned,
                last_confirmed_at,
                created_at
            FROM facts
            WHERE status = 'active'
            ORDER BY id ASC
        """)
        facts = cur.fetchall()

        seen = {}
        to_supersede = []

        for fact in facts:
            fact_id = fact["id"]
            text = fact["fact_text"].lower().strip()
            category = fact["category"]
            confidence = fact["confidence"] or 0.0
            is_pinned = fact["is_pinned"] or 0
            last_confirmed_at = fact["last_confirmed_at"] or ""
            created_at = fact["created_at"] or ""

            key = f"{category}:{text}"

            current_score = (
                confidence
                + (0.5 if is_pinned else 0.0)
                + (0.1 if last_confirmed_at else 0.0)
            )

            if key in seen:
                existing = seen[key]
                existing_score = existing["score"]

                if current_score <= existing_score:
                    to_supersede.append(fact_id)
                else:
                    to_supersede.append(existing["id"])
                    seen[key] = {
                        "id": fact_id,
                        "score": current_score,
                        "created_at": created_at
                    }
            else:
                seen[key] = {
                    "id": fact_id,
                    "score": current_score,
                    "created_at": created_at
                }

        consolidated = 0
        for fact_id in to_supersede:
            cur.execute("""
                UPDATE facts
                SET
                    status = 'superseded',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status = 'active'
            """, (fact_id,))
            consolidated += cur.rowcount

        conn.commit()
        conn.close()

        return consolidated

    def auto_daily_learning(self) -> Optional[Dict]:
        """
        Auto-create daily learning if one doesn't exist for today.
        Called periodically or on startup.
        """
        today = str(date.today())

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM daily_learnings
            WHERE learning_date = ?
        """, (today,))
        existing = cur.fetchone()
        conn.close()

        if existing:
            return None

        return self.evolution_service.create_daily_learning()

    def get_memory_stats(self) -> Dict:
        """
        Get current memory statistics for monitoring.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as count FROM conversations")
        conversations = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM messages")
        messages = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM facts")
        facts = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM facts WHERE status = 'active'")
        active_facts = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM facts WHERE status = 'superseded'")
        superseded_facts = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM episodic_memories")
        episodes = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM reflections")
        reflections = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM daily_learnings")
        daily_learnings = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM weekly_learnings")
        weekly_learnings = cur.fetchone()["count"]

        conn.close()

        return {
            "conversations": conversations,
            "messages": messages,
            "facts": facts,
            "active_facts": active_facts,
            "superseded_facts": superseded_facts,
            "episodic_memories": episodes,
            "reflections": reflections,
            "daily_learnings": daily_learnings,
            "weekly_learnings": weekly_learnings,
            "timestamp": datetime.now().isoformat()
        }

    def prioritize_memories(self) -> Dict:
        """
        Score and prioritize memories based on recency and importance.
        Returns summary of prioritized memory landscape.
        """
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT category, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM facts
            GROUP BY category
            ORDER BY count DESC
        """)
        fact_categories = [dict(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT importance, COUNT(*) as count
            FROM episodic_memories
            GROUP BY importance
            ORDER BY importance DESC
        """)
        episode_priorities = [dict(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT reflection_type, COUNT(*) as count
            FROM reflections
            GROUP BY reflection_type
            ORDER BY count DESC
        """)
        reflection_types = [dict(row) for row in cur.fetchall()]

        conn.close()

        return {
            "fact_categories": fact_categories,
            "episode_priorities": episode_priorities,
            "reflection_types": reflection_types
        }

    def run_startup_consolidation(self) -> Dict:
        """
        Run consolidation checks on startup.
        - Create daily learning if needed
        - Consolidate facts
        - Return stats
        """
        results = {
            "daily_learning_created": False,
            "facts_consolidated": 0,
            "stats": None
        }

        daily_learning = self.auto_daily_learning()
        if daily_learning and daily_learning.get("success"):
            results["daily_learning_created"] = True
            results["daily_learning_id"] = daily_learning.get("daily_learning_id")

        results["facts_consolidated"] = self.consolidate_facts()
        results["stats"] = self.get_memory_stats()

        return results

    def _get_conversation_episode_count(self, conversation_id: int) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) as count FROM episodic_memories
            WHERE conversation_id = ?
        """, (conversation_id,))

        count = cur.fetchone()["count"]
        conn.close()

        return count
