import json
import logging
from typing import Dict, Any


class ObservabilityService:
    def __init__(self):
        self.logger = logging.getLogger("mnemosyne")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, payload: Dict[str, Any], level: str = "info"):
        message = json.dumps({
            "event_type": event_type,
            "payload": payload
        }, default=str)

        if level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)

    def log_chat_request(
        self,
        conversation_id: int,
        query_type: str,
        retrieval_mode: str,
        model_used: str
    ):
        self.log_event("chat_request", {
            "conversation_id": conversation_id,
            "query_type": query_type,
            "retrieval_mode": retrieval_mode,
            "model_used": model_used
        })

    def log_retrieval_context(
        self,
        conversation_id: int,
        context_package: Dict[str, Any]
    ):
        self.log_event("retrieval_context", {
            "conversation_id": conversation_id,
            "query_type": context_package.get("query_type"),
            "retrieval_mode": context_package.get("retrieval_mode"),
            "retrieval_plan": context_package.get("retrieval_plan"),
            "context_counts": context_package.get("context_counts"),
            "context_usage": context_package.get("context_usage"),
            "active_project_id": context_package.get("active_project_id")
        })

    def log_memory_extraction(
        self,
        conversation_id: int,
        facts_extracted_count: int,
        continuity_summary: Dict[str, Any]
    ):
        self.log_event("memory_extraction", {
            "conversation_id": conversation_id,
            "facts_extracted_count": facts_extracted_count,
            "continuity_projects": len(continuity_summary.get("projects", [])),
            "continuity_goals": len(continuity_summary.get("goals", [])),
            "continuity_open_loops": len(continuity_summary.get("open_loops", []))
        })

    def log_background_consolidation(
        self,
        conversation_id: int,
        result: Dict[str, Any]
    ):
        self.log_event("background_consolidation", {
            "conversation_id": conversation_id,
            "result": result
        })

    def log_error(
        self,
        event_type: str,
        error: str,
        extra: Dict[str, Any] | None = None
    ):
        payload = {"error": error}
        if extra:
            payload.update(extra)
        self.log_event(event_type, payload, level="error")
