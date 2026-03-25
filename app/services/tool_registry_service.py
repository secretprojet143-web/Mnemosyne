from typing import Dict, List, Optional


class ToolRegistryService:
    def __init__(self):
        self._tools = {
            "calculator": {
                "name": "calculator",
                "description": "Evaluate simple mathematical expressions safely.",
                "category": "utility",
                "risk_level": "low",
                "requires_confirmation": False,
                "enabled": True,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "number"}
                    },
                    "required": ["result"]
                }
            },
            "file_read": {
                "name": "file_read",
                "description": "Read the contents of an allowed file path.",
                "category": "file",
                "risk_level": "medium",
                "requires_confirmation": False,
                "enabled": True,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"}
                    },
                    "required": ["content"]
                }
            },
            "file_write": {
                "name": "file_write",
                "description": "Write content to an allowed file path.",
                "category": "file",
                "risk_level": "high",
                "requires_confirmation": True,
                "enabled": True,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"}
                    },
                    "required": ["success"]
                }
            },
            "memory_lookup": {
                "name": "memory_lookup",
                "description": "Query internal structured or semantic memory.",
                "category": "knowledge",
                "risk_level": "low",
                "requires_confirmation": False,
                "enabled": True,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"}
                    },
                    "required": ["results"]
                }
            }
        }

    def list_tools(self) -> List[Dict]:
        return sorted(self._tools.values(), key=lambda x: x["name"])

    def get_tool(self, tool_name: str) -> Optional[Dict]:
        return self._tools.get(tool_name)

    def tool_exists(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def list_enabled_tools(self) -> List[Dict]:
        return [tool for tool in self.list_tools() if tool.get("enabled", False)]

    # --------------------
    # Input Schema Validation
    # --------------------
    def validate_tool_input(self, tool_name: str, payload: Dict) -> Dict:
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "valid": False,
                "errors": [f"Tool '{tool_name}' not found."],
                "warnings": [],
                "tool_name": tool_name
            }

        schema = tool.get("input_schema", {})
        return self._validate_payload_against_schema(
            tool_name=tool_name,
            payload=payload,
            schema=schema
        )

    def _validate_payload_against_schema(self, tool_name: str, payload: Dict, schema: Dict) -> Dict:
        errors = []
        warnings = []

        schema_type = schema.get("type")
        if schema_type != "object":
            errors.append("Only object input schemas are currently supported.")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "tool_name": tool_name
            }

        if not isinstance(payload, dict):
            errors.append("Payload must be an object.")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "tool_name": tool_name
            }

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for field in required:
            if field not in payload:
                errors.append(f"Missing required field: {field}")

        for field, value in payload.items():
            field_schema = properties.get(field)
            if not field_schema:
                warnings.append(f"Unexpected field provided: {field}")
                continue

            expected_type = field_schema.get("type")
            if not self._value_matches_type(value, expected_type):
                errors.append(
                    f"Field '{field}' has invalid type. Expected {expected_type}, got {type(value).__name__}"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "tool_name": tool_name
        }

    def _value_matches_type(self, value, expected_type: Optional[str]) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        return True
