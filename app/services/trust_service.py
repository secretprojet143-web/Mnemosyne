from typing import Dict, List


class TrustService:
    def __init__(self):
        self.source_map = {
            "system": {
                "trust_level": "trusted",
                "can_issue_instructions": True,
                "can_trigger_actions": True
            },
            "user": {
                "trust_level": "semi_trusted",
                "can_issue_instructions": True,
                "can_trigger_actions": False
            },
            "memory": {
                "trust_level": "semi_trusted",
                "can_issue_instructions": False,
                "can_trigger_actions": False
            },
            "document": {
                "trust_level": "untrusted",
                "can_issue_instructions": False,
                "can_trigger_actions": False
            },
            "tool_output": {
                "trust_level": "untrusted",
                "can_issue_instructions": False,
                "can_trigger_actions": False
            },
            "external": {
                "trust_level": "untrusted",
                "can_issue_instructions": False,
                "can_trigger_actions": False
            }
        }

    def get_source_policy(self, source_type: str) -> Dict:
        return self.source_map.get(
            source_type,
            {
                "trust_level": "untrusted",
                "can_issue_instructions": False,
                "can_trigger_actions": False
            }
        )

    def classify_source(self, source_type: str) -> Dict:
        policy = self.get_source_policy(source_type)

        return {
            "source_type": source_type,
            "trust_level": policy["trust_level"],
            "can_issue_instructions": policy["can_issue_instructions"],
            "can_trigger_actions": policy["can_trigger_actions"]
        }

    def annotate_item(self, item: Dict, source_type: str, content_key: str = "content") -> Dict:
        policy = self.classify_source(source_type)

        annotated = dict(item)
        annotated["_trust_source"] = source_type
        annotated["_trust_level"] = policy["trust_level"]
        annotated["_can_issue_instructions"] = policy["can_issue_instructions"]
        annotated["_can_trigger_actions"] = policy["can_trigger_actions"]

        return annotated

    def annotate_items(self, items: List[Dict], source_type: str, content_key: str = "content") -> List[Dict]:
        return [
            self.annotate_item(item, source_type=source_type, content_key=content_key)
            for item in items
        ]
