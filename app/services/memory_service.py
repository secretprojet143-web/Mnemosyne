import re
from typing import List, Dict, Optional

from app.db.database import get_connection
from app.services.fact_extractor import FactExtractor


class MemoryService:
    def __init__(self):
        self.fact_extractor = FactExtractor()

    def _parse_fact_signature(self, fact_text: str) -> Optional[Dict]:
        text = fact_text.strip()

        patterns = [
            {"kind": "name", "pattern": r"^User's name is (.+)$"},
            {"kind": "location_live", "pattern": r"^User lives in (.+)$"},
            {"kind": "work_role", "pattern": r"^User works as (.+)$"},
            {"kind": "work_company", "pattern": r"^User works at (.+)$"},
            {"kind": "education_learning", "pattern": r"^User is learning (.+)$"},
            {"kind": "education_studies", "pattern": r"^User studies (.+)$"},
        ]

        for item in patterns:
            match = re.match(item["pattern"], text, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip().lower()
                return {"kind": item["kind"], "value": value}

        return None

    def _facts_conflict(self, existing_fact_text: str, new_fact_text: str, category: str) -> bool:
        existing_sig = self._parse_fact_signature(existing_fact_text)
        new_sig = self._parse_fact_signature(new_fact_text)

        if not existing_sig or not new_sig:
            return False

        if existing_sig["kind"] != new_sig["kind"]:
            return False

        conflict_kinds = {"name", "location_live", "work_role", "work_company"}

        if existing_sig["kind"] not in conflict_kinds:
            return False

        return existing_sig["value"] != new_sig["value"]

    def find_conflicting_active_fact(self, fact_text: str, category: str) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, conversation_id, source_message_id, fact_text, category,
                confidence, status, visibility, is_pinned, provenance,
                supersedes_fact_id, created_at, updated_at, last_confirmed_at
            FROM facts
            WHERE status = 'active' AND category = ?
            ORDER BY is_pinned DESC, confidence DESC, id DESC
        """, (category,))

        rows = cur.fetchall()
        conn.close()

        for row in rows:
            existing_fact = dict(row)
            if self._facts_conflict(existing_fact["fact_text"], fact_text, category):
                return existing_fact

        return None

    def create_conversation(self, title: Optional[str] = None) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (title or "New Conversation",)
        )

        conversation_id = cur.lastrowid
        conn.commit()
        conn.close()
        return conversation_id

    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model_used: Optional[str] = None
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO messages (conversation_id, role, content, model_used)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, role, content, model_used))

        message_id = cur.lastrowid

        cur.execute("""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (conversation_id,))

        conn.commit()
        conn.close()

        return message_id

    def get_recent_messages(self, conversation_id: int, limit: int = 12) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT role, content, created_at, model_used
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (conversation_id, limit))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in reversed(rows)]

    def get_conversation_messages(self, conversation_id: int) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, role, content, model_used, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def list_conversations(self, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, created_at, updated_at, project_id
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def link_conversation_to_project(self, conversation_id: int, project_id: int) -> bool:
        if not self.conversation_exists(conversation_id):
            return False

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE conversations
            SET project_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (project_id, conversation_id))

        conn.commit()
        conn.close()
        return True

    def get_conversation_project_id(self, conversation_id: int) -> Optional[int]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT project_id
            FROM conversations
            WHERE id = ?
        """, (conversation_id,))

        row = cur.fetchone()
        conn.close()

        if row:
            return row["project_id"]
        return None

    def get_conversations_by_project(self, project_id: int, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, created_at, updated_at, project_id
            FROM conversations
            WHERE project_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (project_id, limit))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def extract_and_store_facts(
        self,
        conversation_id: int,
        user_message: str,
        source_message_id: Optional[int] = None
    ) -> List[Dict]:
        facts = self.fact_extractor.extract(user_message)

        if not facts:
            return []

        conn = get_connection()
        cur = conn.cursor()

        stored = []

        for fact in facts:
            fact_text = fact["fact_text"].strip()

            cur.execute("""
                SELECT id, confidence, category, visibility, provenance, is_pinned
                FROM facts
                WHERE LOWER(fact_text) = LOWER(?)
                  AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
            """, (fact_text,))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE facts
                    SET
                        confidence = CASE
                            WHEN confidence < ? THEN ?
                            ELSE confidence
                        END,
                        last_confirmed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    fact["confidence"],
                    fact["confidence"],
                    existing["id"]
                ))

                stored.append({
                    "id": existing["id"],
                    "fact_text": fact_text,
                    "category": existing["category"],
                    "confidence": max(existing["confidence"], fact["confidence"]),
                    "status": "active",
                    "visibility": existing["visibility"],
                    "provenance": existing["provenance"],
                    "source_message_id": source_message_id,
                    "last_confirmed": True,
                    "action": "reconfirmed",
                    "extraction_pattern": fact.get("extraction_pattern"),
                    "durability": fact.get("durability")
                })
                continue

            conflicting_fact = self.find_conflicting_active_fact(
                fact_text=fact_text,
                category=fact["category"]
            )

            if conflicting_fact:
                cur.execute("""
                    UPDATE facts
                    SET
                        status = 'superseded',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (conflicting_fact["id"],))

                cur.execute("""
                    INSERT INTO facts (
                        conversation_id, source_message_id, fact_text, category,
                        confidence, status, visibility, is_pinned, provenance,
                        supersedes_fact_id
                    )
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
                """, (
                    conversation_id,
                    source_message_id,
                    fact_text,
                    fact["category"],
                    fact["confidence"],
                    fact.get("visibility", conflicting_fact["visibility"]),
                    fact.get("is_pinned", 0),
                    fact.get("provenance", "explicit"),
                    conflicting_fact["id"]
                ))

                new_fact_id = cur.lastrowid

                stored.append({
                    "id": new_fact_id,
                    "fact_text": fact_text,
                    "category": fact["category"],
                    "confidence": fact["confidence"],
                    "status": "active",
                    "visibility": fact.get("visibility", conflicting_fact["visibility"]),
                    "provenance": fact.get("provenance", "explicit"),
                    "source_message_id": source_message_id,
                    "supersedes_fact_id": conflicting_fact["id"],
                    "action": "superseded_conflict",
                    "extraction_pattern": fact.get("extraction_pattern"),
                    "durability": fact.get("durability")
                })
                continue

            cur.execute("""
                INSERT INTO facts (
                    conversation_id, source_message_id, fact_text, category,
                    confidence, status, visibility, is_pinned, provenance
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                source_message_id,
                fact_text,
                fact["category"],
                fact["confidence"],
                fact.get("status", "active"),
                fact.get("visibility", "personal"),
                fact.get("is_pinned", 0),
                fact.get("provenance", "explicit")
            ))

            stored.append({
                "id": cur.lastrowid,
                "fact_text": fact_text,
                "category": fact["category"],
                "confidence": fact["confidence"],
                "status": fact.get("status", "active"),
                "visibility": fact.get("visibility", "personal"),
                "provenance": fact.get("provenance", "explicit"),
                "source_message_id": source_message_id,
                "action": "created",
                "extraction_pattern": fact.get("extraction_pattern"),
                "durability": fact.get("durability")
            })

        conn.commit()
        conn.close()

        return stored

    def get_all_facts(self) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance,
                supersedes_fact_id,
                created_at,
                updated_at,
                last_confirmed_at
            FROM facts
            ORDER BY id DESC
        """)

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_facts_by_category(self, category: str) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance,
                supersedes_fact_id,
                created_at,
                updated_at,
                last_confirmed_at
            FROM facts
            WHERE category = ?
              AND status = 'active'
            ORDER BY id DESC
        """, (category,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_fact_by_id(self, fact_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance,
                supersedes_fact_id,
                created_at,
                updated_at,
                last_confirmed_at
            FROM facts
            WHERE id = ?
        """, (fact_id,))

        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_active_facts(self) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance,
                supersedes_fact_id,
                created_at,
                updated_at,
                last_confirmed_at
            FROM facts
            WHERE status = 'active'
            ORDER BY is_pinned DESC, confidence DESC, last_confirmed_at DESC, id DESC
        """)

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_prompt_safe_facts(self, limit: int = 20) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, conversation_id, source_message_id, fact_text, category,
                confidence, status, visibility, is_pinned, provenance,
                supersedes_fact_id, created_at, updated_at, last_confirmed_at
            FROM facts
            WHERE status = 'active'
              AND visibility IN ('general', 'personal', 'sensitive')
            ORDER BY is_pinned DESC, confidence DESC, last_confirmed_at DESC, id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_profile_facts(self) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, conversation_id, source_message_id, fact_text, category,
                confidence, status, visibility, is_pinned, provenance,
                supersedes_fact_id, created_at, updated_at, last_confirmed_at
            FROM facts
            WHERE status = 'active'
              AND visibility IN ('general', 'personal', 'sensitive')
            ORDER BY is_pinned DESC, confidence DESC, last_confirmed_at DESC, id DESC
        """)

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_facts_by_status(self, status: str) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance,
                supersedes_fact_id,
                created_at,
                updated_at,
                last_confirmed_at
            FROM facts
            WHERE status = ?
            ORDER BY id DESC
        """, (status,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_facts_by_visibility(self, visibility: str) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                conversation_id,
                source_message_id,
                fact_text,
                category,
                confidence,
                status,
                visibility,
                is_pinned,
                provenance,
                supersedes_fact_id,
                created_at,
                updated_at,
                last_confirmed_at
            FROM facts
            WHERE visibility = ?
            ORDER BY id DESC
        """, (visibility,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_fact_provenance(self, fact_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                f.id AS fact_id,
                f.fact_text,
                f.category,
                f.confidence,
                f.status,
                f.visibility,
                f.is_pinned,
                f.provenance,
                f.created_at AS fact_created_at,
                f.updated_at AS fact_updated_at,
                f.last_confirmed_at,
                f.supersedes_fact_id,
                f.conversation_id,
                c.title AS conversation_title,
                c.created_at AS conversation_created_at,
                m.id AS source_message_id,
                m.role AS source_message_role,
                m.content AS source_message_content,
                m.model_used AS source_message_model_used,
                m.created_at AS source_message_created_at
            FROM facts f
            LEFT JOIN conversations c ON f.conversation_id = c.id
            LEFT JOIN messages m ON f.source_message_id = m.id
            WHERE f.id = ?
        """, (fact_id,))

        row = cur.fetchone()
        conn.close()

        return dict(row) if row else None

    def fact_exists(self, fact_id: int) -> bool:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM facts WHERE id = ?", (fact_id,))
        row = cur.fetchone()
        conn.close()

        return row is not None

    def update_fact(
        self,
        fact_id: int,
        fact_text: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        visibility: Optional[str] = None,
        provenance: Optional[str] = None,
        is_pinned: Optional[int] = None
    ) -> Optional[Dict]:
        existing = self.get_fact_by_id(fact_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE facts
            SET
                fact_text = ?,
                category = ?,
                confidence = ?,
                visibility = ?,
                provenance = ?,
                is_pinned = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            fact_text if fact_text is not None else existing["fact_text"],
            category if category is not None else existing["category"],
            confidence if confidence is not None else existing["confidence"],
            visibility if visibility is not None else existing["visibility"],
            provenance if provenance is not None else existing["provenance"],
            is_pinned if is_pinned is not None else existing["is_pinned"],
            fact_id
        ))

        conn.commit()
        conn.close()

        return self.get_fact_by_id(fact_id)

    def soft_delete_fact(self, fact_id: int) -> Optional[Dict]:
        if not self.fact_exists(fact_id):
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE facts
            SET
                status = 'deleted',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (fact_id,))

        conn.commit()
        conn.close()

        return self.get_fact_by_id(fact_id)

    def pin_fact(self, fact_id: int, pinned: bool = True) -> Optional[Dict]:
        if not self.fact_exists(fact_id):
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE facts
            SET
                is_pinned = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if pinned else 0, fact_id))

        conn.commit()
        conn.close()

        return self.get_fact_by_id(fact_id)

    def mark_fact_status(self, fact_id: int, status: str) -> Optional[Dict]:
        allowed_statuses = {"active", "superseded", "outdated", "uncertain", "deleted"}
        if status not in allowed_statuses:
            raise ValueError(f"Invalid status: {status}")

        if not self.fact_exists(fact_id):
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE facts
            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, fact_id))

        conn.commit()
        conn.close()

        return self.get_fact_by_id(fact_id)

    def supersede_fact(
        self,
        old_fact_id: int,
        new_fact_text: str,
        category: Optional[str] = None,
        confidence: float = 0.9,
        visibility: str = "personal",
        provenance: str = "corrected",
        is_pinned: int = 0
    ) -> Optional[Dict]:
        old_fact = self.get_fact_by_id(old_fact_id)
        if not old_fact:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE facts
            SET
                status = 'superseded',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (old_fact_id,))

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
                provenance,
                supersedes_fact_id
            )
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
        """, (
            old_fact["conversation_id"],
            old_fact["source_message_id"],
            new_fact_text.strip(),
            category if category is not None else old_fact["category"],
            confidence,
            visibility,
            is_pinned,
            provenance,
            old_fact_id
        ))

        new_fact_id = cur.lastrowid

        conn.commit()
        conn.close()

        return self.get_fact_by_id(new_fact_id)

    def conversation_exists(self, conversation_id: int) -> bool:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        row = cur.fetchone()
        conn.close()

        return row is not None

    def get_fact_stats(self) -> Dict:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS count FROM facts")
        total_facts = cur.fetchone()["count"]

        cur.execute("SELECT status, COUNT(*) AS count FROM facts GROUP BY status")
        by_status = {row["status"]: row["count"] for row in cur.fetchall()}

        cur.execute("SELECT category, COUNT(*) AS count FROM facts GROUP BY category ORDER BY count DESC")
        by_category = {row["category"]: row["count"] for row in cur.fetchall()}

        cur.execute("SELECT visibility, COUNT(*) AS count FROM facts GROUP BY visibility")
        by_visibility = {row["visibility"]: row["count"] for row in cur.fetchall()}

        cur.execute("SELECT COUNT(*) AS count FROM facts WHERE is_pinned = 1")
        pinned_count = cur.fetchone()["count"]

        cur.execute("""
            SELECT COUNT(*) AS count FROM facts
            WHERE status = 'active' AND visibility IN ('general', 'personal', 'sensitive')
        """)
        prompt_safe_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM facts WHERE confidence >= 0.9")
        high_confidence = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM facts WHERE confidence >= 0.75 AND confidence < 0.9")
        medium_confidence = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM facts WHERE confidence < 0.75")
        low_confidence = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM facts WHERE status = 'superseded'")
        superseded_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) AS count FROM facts WHERE supersedes_fact_id IS NOT NULL")
        replacement_count = cur.fetchone()["count"]

        cur.execute("""
            SELECT COUNT(*) AS count FROM facts
            WHERE datetime(created_at) >= datetime('now', '-7 days')
        """)
        created_last_7_days = cur.fetchone()["count"]

        conn.close()

        return {
            "total_facts": total_facts,
            "by_status": by_status,
            "by_category": by_category,
            "by_visibility": by_visibility,
            "pinned_count": pinned_count,
            "prompt_safe_count": prompt_safe_count,
            "confidence_buckets": {
                "high_confidence_gte_0_9": high_confidence,
                "medium_confidence_0_75_to_0_89": medium_confidence,
                "low_confidence_lt_0_75": low_confidence
            },
            "supersession": {
                "superseded_count": superseded_count,
                "replacement_count": replacement_count
            },
            "recent_activity": {
                "created_last_7_days": created_last_7_days
            }
        }

    def get_recent_fact_activity(self, limit: int = 20) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, fact_text, category, confidence, status, visibility,
                is_pinned, provenance, supersedes_fact_id,
                created_at, updated_at, last_confirmed_at
            FROM facts
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_fact_history(self, fact_text: str) -> List[Dict]:
        signature = self._parse_fact_signature(fact_text)
        if not signature:
            return []

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, conversation_id, source_message_id, fact_text, category,
                confidence, status, visibility, is_pinned, provenance,
                supersedes_fact_id, created_at, updated_at, last_confirmed_at
            FROM facts
            ORDER BY created_at ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()

        matching = []
        for row in rows:
            item = dict(row)
            item_sig = self._parse_fact_signature(item["fact_text"])
            if item_sig and item_sig["kind"] == signature["kind"]:
                matching.append(item)

        return matching

    def get_fact_timeline_by_kind(self, kind: str) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, conversation_id, source_message_id, fact_text, category,
                confidence, status, visibility, is_pinned, provenance,
                supersedes_fact_id, created_at, updated_at, last_confirmed_at
            FROM facts
            ORDER BY created_at ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()

        matching = []
        for row in rows:
            item = dict(row)
            item_sig = self._parse_fact_signature(item["fact_text"])
            if item_sig and item_sig["kind"] == kind:
                enriched = dict(item)
                enriched["parsed_kind"] = item_sig["kind"]
                enriched["parsed_value"] = item_sig["value"]
                matching.append(enriched)

        return matching

    def get_temporal_fact_groups(self) -> Dict:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id, conversation_id, source_message_id, fact_text, category,
                confidence, status, visibility, is_pinned, provenance,
                supersedes_fact_id, created_at, updated_at, last_confirmed_at
            FROM facts
            ORDER BY created_at ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()

        groups = {}

        for row in rows:
            item = dict(row)
            item_sig = self._parse_fact_signature(item["fact_text"])
            if not item_sig:
                continue

            kind = item_sig["kind"]

            if kind not in {"name", "location_live", "work_role", "work_company"}:
                continue

            enriched = dict(item)
            enriched["parsed_kind"] = item_sig["kind"]
            enriched["parsed_value"] = item_sig["value"]

            groups.setdefault(kind, []).append(enriched)

        return groups
