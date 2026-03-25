from typing import Dict

from app.services.tool_registry_service import ToolRegistryService
from app.services.trust_service import TrustService


class PermissionService:
    def __init__(self):
        self.tool_registry = ToolRegistryService()
        self.trust_service = TrustService()

    def _get_human_readable_reason(self, tool_name: str, source_type: str, risk_level: str, situation: str) -> str:
        tool = self.tool_registry.get_tool(tool_name)
        tool_desc = tool.get("description", tool_name) if tool else tool_name

        risk_descriptions = {
            "low": "This is a safe, read-only action",
            "medium": "This action could have moderate effects",
            "high": "This action can modify files or data",
            "critical": "This action is potentially destructive"
        }

        source_descriptions = {
            "user": "your direct request",
            "system": "system instructions",
            "memory": "stored memories",
            "document": "a document you uploaded",
            "tool_output": "output from a previous tool",
            "external": "external content"
        }

        if situation == "blocked_by_source":
            return (
                f"This action was blocked because it was triggered by {source_descriptions.get(source_type, source_type)}, "
                f"which cannot directly authorize actions. Only your direct requests or system instructions can trigger tools."
            )

        if situation == "needs_confirmation":
            return (
                f"The tool '{tool_name}' ({tool_desc}) requires confirmation because: "
                f"{risk_descriptions.get(risk_level, 'it has unknown risk')}. "
                f"To proceed, please confirm this action explicitly."
            )

        return "Permission granted."

    def check_tool_permission(
        self,
        tool_name: str,
        source_type: str,
        confirmed: bool = False
    ) -> Dict:
        tool = self.tool_registry.get_tool(tool_name)
        trust = self.trust_service.classify_source(source_type)

        if not tool:
            return {
                "allowed": False,
                "requires_confirmation": False,
                "reason": f"Tool '{tool_name}' not found.",
                "human_reason": f"I don't have a tool called '{tool_name}'.",
                "tool_name": tool_name,
                "source_type": source_type,
                "trust_level": trust["trust_level"]
            }

        risk_level = tool.get("risk_level", "low")
        requires_confirmation = bool(tool.get("requires_confirmation", False))

        if not trust["can_trigger_actions"] and source_type in {"memory", "document", "tool_output", "external"}:
            return {
                "allowed": False,
                "requires_confirmation": False,
                "reason": f"Source type '{source_type}' is not allowed to directly trigger tool actions.",
                "human_reason": self._get_human_readable_reason(tool_name, source_type, risk_level, "blocked_by_source"),
                "tool_name": tool_name,
                "source_type": source_type,
                "trust_level": trust["trust_level"],
                "risk_level": risk_level
            }

        if requires_confirmation and not confirmed:
            return {
                "allowed": False,
                "requires_confirmation": True,
                "reason": f"Tool '{tool_name}' requires explicit confirmation.",
                "human_reason": self._get_human_readable_reason(tool_name, source_type, risk_level, "needs_confirmation"),
                "tool_name": tool_name,
                "source_type": source_type,
                "trust_level": trust["trust_level"],
                "risk_level": risk_level
            }

        return {
            "allowed": True,
            "requires_confirmation": requires_confirmation,
            "reason": "Permission granted.",
            "human_reason": "This action is allowed and can proceed.",
            "tool_name": tool_name,
            "source_type": source_type,
            "trust_level": trust["trust_level"],
            "risk_level": risk_level
        }
