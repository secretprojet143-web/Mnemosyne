from typing import List, Dict, Optional

from app.db.database import get_connection


class ContinuityService:
    def create_project(
        self,
        title: str,
        description: str = "",
        status: str = "active",
        priority: str = "medium"
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO projects (title, description, status, priority)
            VALUES (?, ?, ?, ?)
        """, (title.strip(), description.strip(), status, priority))

        project_id = cur.lastrowid
        conn.commit()
        conn.close()
        return project_id

    def list_projects(self, status: Optional[str] = None) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        if status:
            cur.execute("""
                SELECT id, title, description, status, priority, created_at, updated_at
                FROM projects
                WHERE status = ?
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END DESC,
                    updated_at DESC
            """, (status,))
        else:
            cur.execute("""
                SELECT id, title, description, status, priority, created_at, updated_at
                FROM projects
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END DESC,
                    updated_at DESC
            """)

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, description, status, priority, created_at, updated_at
            FROM projects
            WHERE id = ?
        """, (project_id,))

        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_project(
        self,
        project_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_project_by_id(project_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE projects
            SET
                title = ?,
                description = ?,
                status = ?,
                priority = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            title.strip() if title is not None else existing["title"],
            description.strip() if description is not None else existing["description"],
            status if status is not None else existing["status"],
            priority if priority is not None else existing["priority"],
            project_id
        ))

        conn.commit()
        conn.close()
        return self.get_project_by_id(project_id)

    def project_exists(self, project_id: int) -> bool:
        return self.get_project_by_id(project_id) is not None

    def create_goal(
        self,
        goal_text: str,
        project_id: Optional[int] = None,
        status: str = "active",
        priority: str = "medium",
        target_date: Optional[str] = None
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO goals (project_id, goal_text, status, priority, target_date)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, goal_text.strip(), status, priority, target_date))

        goal_id = cur.lastrowid
        conn.commit()
        conn.close()
        return goal_id

    def list_goals(
        self,
        status: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT id, project_id, goal_text, status, priority, target_date, created_at, updated_at
            FROM goals
        """
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                END DESC,
                updated_at DESC
        """

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_goal_by_id(self, goal_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, project_id, goal_text, status, priority, target_date, created_at, updated_at
            FROM goals
            WHERE id = ?
        """, (goal_id,))

        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_goal(
        self,
        goal_id: int,
        goal_text: Optional[str] = None,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        target_date: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_goal_by_id(goal_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE goals
            SET
                project_id = ?,
                goal_text = ?,
                status = ?,
                priority = ?,
                target_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            project_id if project_id is not None else existing["project_id"],
            goal_text.strip() if goal_text is not None else existing["goal_text"],
            status if status is not None else existing["status"],
            priority if priority is not None else existing["priority"],
            target_date if target_date is not None else existing["target_date"],
            goal_id
        ))

        conn.commit()
        conn.close()
        return self.get_goal_by_id(goal_id)

    def goal_exists(self, goal_id: int) -> bool:
        return self.get_goal_by_id(goal_id) is not None

    def create_open_loop(
        self,
        description: str,
        project_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        status: str = "open",
        priority: str = "medium",
        due_date: Optional[str] = None
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO open_loops (project_id, conversation_id, description, status, priority, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, conversation_id, description.strip(), status, priority, due_date))

        loop_id = cur.lastrowid
        conn.commit()
        conn.close()
        return loop_id

    def list_open_loops(
        self,
        status: Optional[str] = None,
        project_id: Optional[int] = None,
        conversation_id: Optional[int] = None
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT id, project_id, conversation_id, description, status, priority, due_date, created_at, updated_at
            FROM open_loops
        """
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)

        if conversation_id is not None:
            conditions.append("conversation_id = ?")
            params.append(conversation_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                END DESC,
                updated_at DESC
        """

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_open_loop_by_id(self, loop_id: int) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, project_id, conversation_id, description, status, priority, due_date, created_at, updated_at
            FROM open_loops
            WHERE id = ?
        """, (loop_id,))

        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_open_loop(
        self,
        loop_id: int,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Optional[Dict]:
        existing = self.get_open_loop_by_id(loop_id)
        if not existing:
            return None

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE open_loops
            SET
                project_id = ?,
                conversation_id = ?,
                description = ?,
                status = ?,
                priority = ?,
                due_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            project_id if project_id is not None else existing["project_id"],
            conversation_id if conversation_id is not None else existing["conversation_id"],
            description.strip() if description is not None else existing["description"],
            status if status is not None else existing["status"],
            priority if priority is not None else existing["priority"],
            due_date if due_date is not None else existing["due_date"],
            loop_id
        ))

        conn.commit()
        conn.close()
        return self.get_open_loop_by_id(loop_id)

    def open_loop_exists(self, loop_id: int) -> bool:
        return self.get_open_loop_by_id(loop_id) is not None

    def find_similar_project(self, title: str) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, description, status, priority, created_at, updated_at
            FROM projects
            WHERE LOWER(title) = LOWER(?)
            LIMIT 1
        """, (title.strip(),))

        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def find_similar_goal(self, goal_text: str) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, project_id, goal_text, status, priority, target_date, created_at, updated_at
            FROM goals
            WHERE LOWER(goal_text) = LOWER(?)
              AND status = 'active'
            LIMIT 1
        """, (goal_text.strip(),))

        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def find_similar_open_loop(self, description: str) -> Optional[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, project_id, conversation_id, description, status, priority, due_date, created_at, updated_at
            FROM open_loops
            WHERE LOWER(description) = LOWER(?)
              AND status = 'open'
            LIMIT 1
        """, (description.strip(),))

        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def auto_store_extracted_items(
        self,
        extracted: Dict[str, List[Dict]],
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> Dict:
        stored_projects = []
        stored_goals = []
        stored_open_loops = []
        effective_project_id = project_id

        for project in extracted.get("projects", []):
            existing = self.find_similar_project(project["title"])
            if existing:
                stored_projects.append({"action": "existing", "project": existing})
                if effective_project_id is None:
                    effective_project_id = existing["id"]
            else:
                new_project_id = self.create_project(
                    title=project["title"],
                    description=project.get("description", ""),
                    status="active",
                    priority="high"
                )
                stored_projects.append({
                    "action": "created",
                    "project": self.get_project_by_id(new_project_id)
                })
                if effective_project_id is None:
                    effective_project_id = new_project_id

        for goal in extracted.get("goals", []):
            existing = self.find_similar_goal(goal["goal_text"])
            if existing:
                stored_goals.append({"action": "existing", "goal": existing})
            else:
                goal_id = self.create_goal(
                    goal_text=goal["goal_text"],
                    project_id=effective_project_id,
                    status="active",
                    priority="high"
                )
                stored_goals.append({
                    "action": "created",
                    "goal": self.get_goal_by_id(goal_id)
                })

        for loop in extracted.get("open_loops", []):
            existing = self.find_similar_open_loop(loop["description"])
            if existing:
                stored_open_loops.append({"action": "existing", "open_loop": existing})
            else:
                loop_id = self.create_open_loop(
                    description=loop["description"],
                    project_id=effective_project_id,
                    conversation_id=conversation_id,
                    status="open",
                    priority="high"
                )
                stored_open_loops.append({
                    "action": "created",
                    "open_loop": self.get_open_loop_by_id(loop_id)
                })

        return {
            "projects": stored_projects,
            "goals": stored_goals,
            "open_loops": stored_open_loops,
            "effective_project_id": effective_project_id
        }

    def find_project_by_title_match(self, text: str) -> Optional[Dict]:
        text_lower = text.lower().strip()
        projects = self.list_projects(status="active")

        best_match = None
        best_length = 0

        for project in projects:
            title = project["title"].strip().lower()
            if title and title in text_lower:
                if len(title) > best_length:
                    best_match = project
                    best_length = len(title)

        return best_match

    def infer_project_for_message(
        self,
        message: str,
        conversation_project_id: Optional[int] = None
    ) -> Optional[Dict]:
        if conversation_project_id is not None:
            project = self.get_project_by_id(conversation_project_id)
            if project and project["status"] == "active":
                return project

        matched = self.find_project_by_title_match(message)
        if matched:
            return matched

        return None

    def get_active_projects(self, limit: int = 5) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, description, status, priority, created_at, updated_at
            FROM projects
            WHERE status = 'active'
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                    END DESC,
                    updated_at DESC
                LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_continuity_snapshot(self) -> Dict:
        projects = self.get_active_projects(limit=10)
        goals = self.get_active_goals(limit=15)
        open_loops = self.get_active_open_loops(limit=20)

        return {
            "counts": {
                "active_projects": len(projects),
                "active_goals": len(goals),
                "open_loops": len(open_loops)
            },
            "projects": projects,
            "goals": goals,
            "open_loops": open_loops,
            "top_priorities": {
                "projects": [p for p in projects if p.get("priority") in ("critical", "high")][:5],
                "goals": [g for g in goals if g.get("priority") in ("critical", "high")][:5],
                "open_loops": [o for o in open_loops if o.get("priority") in ("critical", "high")][:8]
            }
        }

    def suggest_next_actions(self, limit: int = 8) -> List[Dict]:
        actions = []

        open_loops = self.get_active_open_loops(limit=20)
        goals = self.get_active_goals(limit=15)
        projects = self.get_active_projects(limit=10)

        priority_weight = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }

        for loop in open_loops:
            actions.append({
                "type": "open_loop",
                "text": loop["description"],
                "priority": loop["priority"],
                "score": priority_weight.get(loop["priority"], 0) + 2,
                "linked_project_id": loop.get("project_id"),
                "linked_conversation_id": loop.get("conversation_id")
            })

        for goal in goals:
            actions.append({
                "type": "goal",
                "text": goal["goal_text"],
                "priority": goal["priority"],
                "score": priority_weight.get(goal["priority"], 0) + 1,
                "linked_project_id": goal.get("project_id"),
                "linked_conversation_id": None
            })

        for project in projects:
            actions.append({
                "type": "project",
                "text": f"Make progress on project: {project['title']}",
                "priority": project["priority"],
                "score": priority_weight.get(project["priority"], 0),
                "linked_project_id": project.get("id"),
                "linked_conversation_id": None
            })

        seen = set()
        deduped = []
        for action in actions:
            key = action["text"].strip().lower()
            if key not in seen:
                seen.add(key)
                deduped.append(action)

        deduped.sort(key=lambda x: x["score"], reverse=True)

        return deduped[:limit]

    def get_active_goals(self, limit: int = 8, project_id: Optional[int] = None) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        if project_id is not None:
            cur.execute("""
                SELECT id, project_id, goal_text, status, priority, target_date, created_at, updated_at
                FROM goals
                WHERE status = 'active' AND project_id = ?
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END DESC,
                    updated_at DESC
                LIMIT ?
            """, (project_id, limit))
        else:
            cur.execute("""
                SELECT id, project_id, goal_text, status, priority, target_date, created_at, updated_at
                FROM goals
                WHERE status = 'active'
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END DESC,
                    updated_at DESC
                LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_active_open_loops(self, limit: int = 10, project_id: Optional[int] = None) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        if project_id is not None:
            cur.execute("""
                SELECT id, project_id, conversation_id, description, status, priority, due_date, created_at, updated_at
                FROM open_loops
                WHERE status = 'open' AND project_id = ?
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END DESC,
                    updated_at DESC
                LIMIT ?
            """, (project_id, limit))
        else:
            cur.execute("""
                SELECT id, project_id, conversation_id, description, status, priority, due_date, created_at, updated_at
                FROM open_loops
                WHERE status = 'open'
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END DESC,
                    updated_at DESC
                LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
