import json
from datetime import date, timedelta
from typing import List, Dict

from app.db.database import get_connection
from app.services.memory_service import MemoryService
from app.services.summarization_service import SummarizationService


class EvolutionService:
    def __init__(self):
        self.memory_service = MemoryService()
        self.summarization_service = SummarizationService()

    def create_episode_for_conversation(self, conversation_id: int) -> Dict:
        messages = self.memory_service.get_conversation_messages(conversation_id)

        if not messages:
            return {"success": False, "message": "No messages found for conversation."}

        summary = self.summarization_service.summarize_conversation(messages)
        reflection = self.summarization_service.generate_structured_reflection(messages)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO episodic_memories (conversation_id, summary, importance)
            VALUES (?, ?, ?)
        """, (conversation_id, summary, 0.75))

        episodic_id = cur.lastrowid

        cur.execute("""
            INSERT INTO reflections (
                conversation_id,
                reflection_text,
                reflection_type,
                user_insights,
                preference_updates,
                project_updates,
                goal_updates,
                potential_conflicts,
                recommended_long_term_memories
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            reflection["reflection_text"],
            reflection["reflection_type"],
            json.dumps(reflection["user_insights"]),
            json.dumps(reflection["preference_updates"]),
            json.dumps(reflection["project_updates"]),
            json.dumps(reflection["goal_updates"]),
            json.dumps(reflection["potential_conflicts"]),
            json.dumps(reflection["recommended_long_term_memories"])
        ))

        reflection_id = cur.lastrowid

        conn.commit()
        conn.close()

        return {
            "success": True,
            "episodic_memory_id": episodic_id,
            "reflection_id": reflection_id,
            "summary": summary,
            "reflection": reflection
        }

    def create_daily_learning(self) -> Dict:
        today = str(date.today())

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT summary FROM episodic_memories
            ORDER BY id DESC
            LIMIT 20
        """)
        episodic_rows = cur.fetchall()

        cur.execute("""
            SELECT
                reflection_text,
                user_insights,
                preference_updates,
                project_updates,
                goal_updates,
                potential_conflicts,
                recommended_long_term_memories
            FROM reflections
            ORDER BY id DESC
            LIMIT 20
        """)
        reflection_rows = cur.fetchall()

        conn.close()

        episodic_texts = [row["summary"] for row in episodic_rows]
        reflection_texts = [row["reflection_text"] for row in reflection_rows]

        user_insights = []
        preference_updates = []
        project_updates = []
        goal_updates = []
        potential_conflicts = []
        recommended_long_term_memories = []

        for row in reflection_rows:
            user_insights.extend(self._parse_json_list(row["user_insights"]))
            preference_updates.extend(self._parse_json_list(row["preference_updates"]))
            project_updates.extend(self._parse_json_list(row["project_updates"]))
            goal_updates.extend(self._parse_json_list(row["goal_updates"]))
            potential_conflicts.extend(self._parse_json_list(row["potential_conflicts"]))
            recommended_long_term_memories.extend(
                self._parse_json_list(row["recommended_long_term_memories"])
            )

        user_insights = self._dedupe_list(user_insights)
        preference_updates = self._dedupe_list(preference_updates)
        project_updates = self._dedupe_list(project_updates)
        goal_updates = self._dedupe_list(goal_updates)
        potential_conflicts = self._dedupe_list(potential_conflicts)
        recommended_long_term_memories = self._dedupe_list(recommended_long_term_memories)

        if (
            not episodic_texts
            and not reflection_texts
            and not user_insights
            and not preference_updates
            and not project_updates
            and not goal_updates
            and not potential_conflicts
            and not recommended_long_term_memories
        ):
            return {"success": False, "message": "No episodic memories or reflections available yet."}

        content = self._build_daily_learning_content(
            episodic_texts=episodic_texts,
            reflection_texts=reflection_texts,
            user_insights=user_insights,
            preference_updates=preference_updates,
            project_updates=project_updates,
            goal_updates=goal_updates,
            potential_conflicts=potential_conflicts,
            recommended_long_term_memories=recommended_long_term_memories
        )

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO daily_learnings (learning_date, content)
            VALUES (?, ?)
        """, (today, content))

        daily_learning_id = cur.lastrowid

        conn.commit()
        conn.close()

        return {
            "success": True,
            "daily_learning_id": daily_learning_id,
            "learning_date": today,
            "content": content,
            "structured_summary": {
                "user_insights": user_insights[:10],
                "preference_updates": preference_updates[:10],
                "project_updates": project_updates[:10],
                "goal_updates": goal_updates[:10],
                "potential_conflicts": potential_conflicts[:10],
                "recommended_long_term_memories": recommended_long_term_memories[:10]
            }
        }

    def list_episodic_memories(self, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, conversation_id, summary, importance, created_at
            FROM episodic_memories
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def list_reflections(self, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                reflection_text,
                reflection_type,
                user_insights,
                preference_updates,
                project_updates,
                goal_updates,
                potential_conflicts,
                recommended_long_term_memories,
                created_at
            FROM reflections
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        reflections = []
        for row in rows:
            item = dict(row)
            for key in [
                "user_insights",
                "preference_updates",
                "project_updates",
                "goal_updates",
                "potential_conflicts",
                "recommended_long_term_memories"
            ]:
                try:
                    item[key] = json.loads(item[key]) if item[key] else []
                except Exception:
                    item[key] = []
            reflections.append(item)

        return reflections

    def list_daily_learnings(self, limit: int = 30) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, learning_date, content, created_at
            FROM daily_learnings
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def _parse_json_list(self, value: str) -> List[str]:
        try:
            parsed = json.loads(value) if value else []
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
        return []

    def _dedupe_list(self, items: List[str]) -> List[str]:
        seen = set()
        result = []

        for item in items:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(item.strip())

        return result

    def _build_daily_learning_content(
        self,
        episodic_texts: List[str],
        reflection_texts: List[str],
        user_insights: List[str],
        preference_updates: List[str],
        project_updates: List[str],
        goal_updates: List[str],
        potential_conflicts: List[str],
        recommended_long_term_memories: List[str]
    ) -> str:
        parts = ["Daily Mnemosyne learning summary:"]

        if episodic_texts:
            parts.append("\nRecent episodic memories:")
            parts.extend(f"- {text}" for text in episodic_texts[:8])

        if reflection_texts:
            parts.append("\nRecent reflection summaries:")
            parts.extend(f"- {text}" for text in reflection_texts[:8])

        if user_insights:
            parts.append("\nKey user insights:")
            parts.extend(f"- {text}" for text in user_insights[:10])

        if preference_updates:
            parts.append("\nPreference updates:")
            parts.extend(f"- {text}" for text in preference_updates[:10])

        if project_updates:
            parts.append("\nProject updates:")
            parts.extend(f"- {text}" for text in project_updates[:10])

        if goal_updates:
            parts.append("\nGoal updates:")
            parts.extend(f"- {text}" for text in goal_updates[:10])

        if potential_conflicts:
            parts.append("\nPotential conflicts or ambiguities:")
            parts.extend(f"- {text}" for text in potential_conflicts[:10])

        if recommended_long_term_memories:
            parts.append("\nRecommended long-term memories:")
            parts.extend(f"- {text}" for text in recommended_long_term_memories[:12])

        return "\n".join(parts)

    def get_recent_reflections(self, limit: int = 5) -> List[Dict]:
        return self.list_reflections(limit=limit)

    def get_recent_daily_learnings(self, limit: int = 3) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, learning_date, content, created_at
            FROM daily_learnings
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_reflection_insight_summary(self, limit: int = 5) -> Dict:
        reflections = self.list_reflections(limit=limit)

        user_insights = []
        preference_updates = []
        project_updates = []
        goal_updates = []
        potential_conflicts = []
        recommended_long_term_memories = []

        for reflection in reflections:
            user_insights.extend(reflection.get("user_insights", []))
            preference_updates.extend(reflection.get("preference_updates", []))
            project_updates.extend(reflection.get("project_updates", []))
            goal_updates.extend(reflection.get("goal_updates", []))
            potential_conflicts.extend(reflection.get("potential_conflicts", []))
            recommended_long_term_memories.extend(
                reflection.get("recommended_long_term_memories", [])
            )

        return {
            "user_insights": self._dedupe_list(user_insights)[:10],
            "preference_updates": self._dedupe_list(preference_updates)[:10],
            "project_updates": self._dedupe_list(project_updates)[:10],
            "goal_updates": self._dedupe_list(goal_updates)[:10],
            "potential_conflicts": self._dedupe_list(potential_conflicts)[:10],
            "recommended_long_term_memories": self._dedupe_list(recommended_long_term_memories)[:10]
        }

    def create_weekly_learning(self) -> Dict:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start.isoformat()}_to_{week_end.isoformat()}"

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM weekly_learnings
            WHERE week_label = ?
        """, (week_label,))
        existing = cur.fetchone()

        if existing:
            conn.close()
            return {
                "success": False,
                "message": "Weekly learning already exists for this week.",
                "week_label": week_label
            }

        cur.execute("""
            SELECT learning_date, content
            FROM daily_learnings
            ORDER BY id DESC
            LIMIT 10
        """)
        daily_rows = cur.fetchall()

        cur.execute("""
            SELECT summary
            FROM episodic_memories
            ORDER BY id DESC
            LIMIT 20
        """)
        episodic_rows = cur.fetchall()

        cur.execute("""
            SELECT
                reflection_text,
                user_insights,
                preference_updates,
                project_updates,
                goal_updates,
                potential_conflicts,
                recommended_long_term_memories
            FROM reflections
            ORDER BY id DESC
            LIMIT 20
        """)
        reflection_rows = cur.fetchall()

        conn.close()

        daily_texts = [row["content"] for row in daily_rows]
        episodic_texts = [row["summary"] for row in episodic_rows]

        user_insights = []
        preference_updates = []
        project_updates = []
        goal_updates = []
        potential_conflicts = []
        recommended_long_term_memories = []

        for row in reflection_rows:
            user_insights.extend(self._parse_json_list(row["user_insights"]))
            preference_updates.extend(self._parse_json_list(row["preference_updates"]))
            project_updates.extend(self._parse_json_list(row["project_updates"]))
            goal_updates.extend(self._parse_json_list(row["goal_updates"]))
            potential_conflicts.extend(self._parse_json_list(row["potential_conflicts"]))
            recommended_long_term_memories.extend(
                self._parse_json_list(row["recommended_long_term_memories"])
            )

        user_insights = self._dedupe_list(user_insights)
        preference_updates = self._dedupe_list(preference_updates)
        project_updates = self._dedupe_list(project_updates)
        goal_updates = self._dedupe_list(goal_updates)
        potential_conflicts = self._dedupe_list(potential_conflicts)
        recommended_long_term_memories = self._dedupe_list(recommended_long_term_memories)

        if (
            not daily_texts
            and not episodic_texts
            and not user_insights
            and not preference_updates
            and not project_updates
            and not goal_updates
            and not potential_conflicts
            and not recommended_long_term_memories
        ):
            return {"success": False, "message": "No data available for weekly learning."}

        content = self._build_weekly_learning_content(
            week_label=week_label,
            daily_texts=daily_texts,
            episodic_texts=episodic_texts,
            user_insights=user_insights,
            preference_updates=preference_updates,
            project_updates=project_updates,
            goal_updates=goal_updates,
            potential_conflicts=potential_conflicts,
            recommended_long_term_memories=recommended_long_term_memories
        )

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO weekly_learnings (week_label, content)
            VALUES (?, ?)
        """, (week_label, content))

        weekly_learning_id = cur.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "weekly_learning_id": weekly_learning_id,
            "week_label": week_label,
            "content": content,
            "structured_summary": {
                "user_insights": user_insights[:12],
                "preference_updates": preference_updates[:12],
                "project_updates": project_updates[:12],
                "goal_updates": goal_updates[:12],
                "potential_conflicts": potential_conflicts[:12],
                "recommended_long_term_memories": recommended_long_term_memories[:15]
            }
        }

    def list_weekly_learnings(self, limit: int = 12) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, week_label, content, created_at
            FROM weekly_learnings
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def _build_weekly_learning_content(
        self,
        week_label: str,
        daily_texts: List[str],
        episodic_texts: List[str],
        user_insights: List[str],
        preference_updates: List[str],
        project_updates: List[str],
        goal_updates: List[str],
        potential_conflicts: List[str],
        recommended_long_term_memories: List[str]
    ) -> str:
        parts = [f"Weekly Mnemosyne synthesis for {week_label}:"]

        if daily_texts:
            parts.append("\nDaily learning highlights:")
            for text in daily_texts[:5]:
                parts.append(f"- {text[:400]}...")

        if episodic_texts:
            parts.append("\nEpisodic memory highlights:")
            parts.extend(f"- {text}" for text in episodic_texts[:10])

        if user_insights:
            parts.append("\nRecurring user insights:")
            parts.extend(f"- {text}" for text in user_insights[:12])

        if preference_updates:
            parts.append("\nPreference patterns:")
            parts.extend(f"- {text}" for text in preference_updates[:12])

        if project_updates:
            parts.append("\nProject evolution:")
            parts.extend(f"- {text}" for text in project_updates[:12])

        if goal_updates:
            parts.append("\nGoal progression:")
            parts.extend(f"- {text}" for text in goal_updates[:12])

        if potential_conflicts:
            parts.append("\nRecurring conflicts or ambiguities:")
            parts.extend(f"- {text}" for text in potential_conflicts[:12])

        if recommended_long_term_memories:
            parts.append("\nStrong candidate long-term memories:")
            parts.extend(f"- {text}" for text in recommended_long_term_memories[:15])

        return "\n".join(parts)
