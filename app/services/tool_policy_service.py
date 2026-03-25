from typing import Dict

from app.services.tool_registry_service import ToolRegistryService


class ToolPolicyService:
    def __init__(self):
        self.tool_registry = ToolRegistryService()

    def authorize_tool_use(
        self,
        tool_name: str,
        confirmed: bool = False,
        initiative_mode: str = "balanced"
    ) -> Dict:
        tool = self.tool_registry.get_tool(tool_name)

        if not tool:
            return {
                "allowed": False,
                "requires_confirmation": False,
                "reason": f"Tool '{tool_name}' not found.",
                "tool_name": tool_name
            }

        if not tool.get("enabled", False):
            return {
                "allowed": False,
                "requires_confirmation": False,
                "reason": "Tool is disabled.",
                "tool_name": tool_name,
                "risk_level": tool.get("risk_level")
            }

        risk_level = tool.get("risk_level", "low")
        requires_confirmation = bool(tool.get("requires_confirmation", False))

        if initiative_mode == "quiet" and risk_level in {"medium", "high", "critical"}:
            return {
                "allowed": False,
                "requires_confirmation": requires_confirmation,
                "reason": f"Tool '{tool_name}' blocked in quiet initiative mode due to risk level '{risk_level}'.",
                "tool_name": tool_name,
                "risk_level": risk_level
            }

        if requires_confirmation and not confirmed:
            return {
                "allowed": False,
                "requires_confirmation": True,
                "reason": f"Tool '{tool_name}' requires confirmation before execution.",
                "tool_name": tool_name,
                "risk_level": risk_level
            }

        return {
            "allowed": True,
            "requires_confirmation": requires_confirmation,
            "reason": "Tool use authorized.",
            "tool_name": tool_name,
            "risk_level": risk_level
        }
