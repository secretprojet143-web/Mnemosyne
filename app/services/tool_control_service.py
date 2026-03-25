import hashlib
import json
from typing import Dict, Any, List, Optional

from app.db.database import get_connection


class ToolControlService:
    def make_payload_signature(self, payload: Dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()

    def record_tool_invocation(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        success: bool,
        error_message: str = ""
    ) -> int:
        signature = self.make_payload_signature(payload)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO tool_invocations (tool_name, payload_signature, success, error_message)
            VALUES (?, ?, ?, ?)
        """, (
            tool_name,
            signature,
            1 if success else 0,
            error_message.strip()
        ))

        invocation_id = cur.lastrowid
        conn.commit()
        conn.close()

        return invocation_id

    def list_recent_tool_invocations(
        self,
        tool_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        conn = get_connection()
        cur = conn.cursor()

        if tool_name:
            cur.execute("""
                SELECT id, tool_name, payload_signature, success, error_message, created_at
                FROM tool_invocations
                WHERE tool_name = ?
                ORDER BY id DESC
                LIMIT ?
            """, (tool_name, limit))
        else:
            cur.execute("""
                SELECT id, tool_name, payload_signature, success, error_message, created_at
                FROM tool_invocations
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def precheck_tool_invocation(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        max_same_payload_failures: int = 2,
        max_tool_failures: int = 4
    ) -> Dict:
        signature = self.make_payload_signature(payload)

        recent = self.list_recent_tool_invocations(tool_name=tool_name, limit=20)

        same_payload_failures = [
            item for item in recent
            if item["payload_signature"] == signature and item["success"] == 0
        ]

        tool_failures = [item for item in recent if item["success"] == 0]

        if len(same_payload_failures) >= max_same_payload_failures:
            return {
                "allowed": False,
                "reason": "Same tool payload has failed too many times recently.",
                "tool_name": tool_name,
                "same_payload_failures": len(same_payload_failures),
                "tool_failures": len(tool_failures),
                "recommended_action": "inspect_or_change_input"
            }

        if len(tool_failures) >= max_tool_failures:
            return {
                "allowed": False,
                "reason": "Tool has failed too many times recently.",
                "tool_name": tool_name,
                "same_payload_failures": len(same_payload_failures),
                "tool_failures": len(tool_failures),
                "recommended_action": "pause_or_inspect_tool"
            }

        return {
            "allowed": True,
            "reason": "Tool invocation precheck passed.",
            "tool_name": tool_name,
            "same_payload_failures": len(same_payload_failures),
            "tool_failures": len(tool_failures),
            "recommended_action": "proceed"
        }
