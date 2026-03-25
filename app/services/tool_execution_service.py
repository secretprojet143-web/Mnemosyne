import ast
import operator
from typing import Dict, Any

from app.services.memory_service import MemoryService
from app.services.tool_registry_service import ToolRegistryService
from app.services.tool_policy_service import ToolPolicyService
from app.services.tool_control_service import ToolControlService
from app.services.permission_service import PermissionService
from app.services.security_scan_service import SecurityScanService
from app.services.trust_service import TrustService


class ToolExecutionService:
    def __init__(self):
        self.tool_registry = ToolRegistryService()
        self.memory_service = MemoryService()
        self.tool_policy = ToolPolicyService()
        self.tool_control = ToolControlService()
        self.permission_service = PermissionService()
        self.security_scan = SecurityScanService()
        self.trust_service = TrustService()

    def execute_tool(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        confirmed: bool = False,
        initiative_mode: str = "balanced",
        source_type: str = "user"
    ) -> Dict[str, Any]:
        input_validation = self.tool_registry.validate_tool_input(tool_name, payload)

        if not input_validation["valid"]:
            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": None,
                "permission": None,
                "precheck": None,
                "execution_success": False,
                "output_validation": None,
                "security_scan": None,
                "result": None,
                "error": "Input validation failed."
            }

        tool = self.tool_registry.get_tool(tool_name)
        if not tool or not tool.get("enabled", False):
            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": None,
                "permission": None,
                "precheck": None,
                "execution_success": False,
                "output_validation": None,
                "security_scan": None,
                "result": None,
                "error": "Tool not found or disabled."
            }

        policy = self.tool_policy.authorize_tool_use(
            tool_name=tool_name,
            confirmed=confirmed,
            initiative_mode=initiative_mode
        )

        if not policy["allowed"]:
            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": policy,
                "permission": None,
                "precheck": None,
                "execution_success": False,
                "output_validation": None,
                "security_scan": None,
                "result": None,
                "error": policy["reason"]
            }

        permission = self.permission_service.check_tool_permission(
            tool_name=tool_name,
            source_type=source_type,
            confirmed=confirmed
        )

        if not permission["allowed"]:
            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": policy,
                "permission": permission,
                "precheck": None,
                "execution_success": False,
                "output_validation": None,
                "security_scan": None,
                "result": None,
                "error": permission["reason"]
            }

        precheck = self.tool_control.precheck_tool_invocation(
            tool_name=tool_name,
            payload=payload
        )

        if not precheck["allowed"]:
            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": policy,
                "permission": permission,
                "precheck": precheck,
                "execution_success": False,
                "output_validation": None,
                "security_scan": None,
                "result": None,
                "error": precheck["reason"]
            }

        try:
            result = self._dispatch_tool(tool_name, payload)

            security_scan = self.security_scan.scan_structured_output(result)

            if security_scan["has_sensitive_data"]:
                redacted_result = self.security_scan.redact_structured_output(result)
            else:
                redacted_result = result

            output_validation = self._validate_tool_output(tool_name, redacted_result)

            trust_metadata = self.trust_service.classify_source("tool_output")

            self.tool_control.record_tool_invocation(
                tool_name=tool_name,
                payload=payload,
                success=output_validation["valid"],
                error_message="" if output_validation["valid"] else "Output validation failed."
            )

            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": policy,
                "permission": permission,
                "precheck": precheck,
                "execution_success": output_validation["valid"],
                "output_validation": output_validation,
                "security_scan": security_scan,
                "trust": trust_metadata,
                "result": redacted_result,
                "error": None if output_validation["valid"] else "Output validation failed."
            }

        except Exception as e:
            self.tool_control.record_tool_invocation(
                tool_name=tool_name,
                payload=payload,
                success=False,
                error_message=str(e)
            )

            return {
                "tool_name": tool_name,
                "input_validation": input_validation,
                "policy": policy,
                "permission": permission,
                "precheck": precheck,
                "execution_success": False,
                "output_validation": None,
                "security_scan": None,
                "trust": None,
                "result": None,
                "error": str(e)
            }

    def _dispatch_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "calculator":
            return self._execute_calculator(payload)

        if tool_name == "memory_lookup":
            return self._execute_memory_lookup(payload)

        raise ValueError(f"Execution for tool '{tool_name}' is not implemented yet.")

    def _execute_calculator(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        expression = payload["expression"]
        result = self._safe_eval(expression)
        return {"result": result}

    def _execute_memory_lookup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = payload["query"].strip().lower()

        facts = self.memory_service.get_prompt_safe_facts(limit=20)
        matched = [
            fact for fact in facts
            if query in fact["fact_text"].lower()
            or query in fact["category"].lower()
        ]

        return {"results": matched[:10]}

    def _validate_tool_output(self, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.tool_registry.get_tool(tool_name)
        schema = tool.get("output_schema", {}) if tool else {}

        return self.tool_registry._validate_payload_against_schema(
            tool_name=tool_name,
            payload=result,
            schema=schema
        )

    def _safe_eval(self, expression: str) -> float:
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_node(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.Num):
                return node.n
            if isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                op_type = type(node.op)
                if op_type not in operators:
                    raise ValueError("Unsupported operator.")
                return operators[op_type](left, right)
            if isinstance(node, ast.UnaryOp):
                operand = eval_node(node.operand)
                op_type = type(node.op)
                if op_type not in operators:
                    raise ValueError("Unsupported unary operator.")
                return operators[op_type](operand)

            raise ValueError("Unsafe or unsupported expression.")

        parsed = ast.parse(expression, mode="eval")
        return eval_node(parsed.body)
