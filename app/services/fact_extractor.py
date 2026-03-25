import re
from typing import List, Dict


class FactExtractor:
    TEMPORARY_IDENTITY_TERMS = {
        "tired", "sleepy", "sad", "happy", "excited", "angry", "upset", "stressed",
        "busy", "confused", "bored", "hungry", "sick", "nervous", "anxious", "fine",
        "okay", "ok", "good", "great", "bad"
    }

    LOW_VALUE_PREFERENCE_TERMS = {
        "this", "that", "it", "things", "stuff"
    }

    def _normalize_value(self, value: str) -> str:
        value = value.strip(" .,!?:;")
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _title_case_if_needed(self, value: str) -> str:
        if value.isupper():
            return value.title()
        return value

    def _is_temporary_identity(self, value: str) -> bool:
        value_clean = value.lower().strip()
        return value_clean in self.TEMPORARY_IDENTITY_TERMS

    def _is_low_value_preference(self, value: str) -> bool:
        value_clean = value.lower().strip()
        return value_clean in self.LOW_VALUE_PREFERENCE_TERMS

    def _build_fact(
        self,
        template: str,
        value: str,
        category: str,
        confidence: float,
        extraction_pattern: str,
        visibility: str = "personal",
        provenance: str = "explicit",
        is_pinned: int = 0,
        durability: str = "medium"
    ) -> Dict:
        normalized = self._normalize_value(value)
        normalized = self._title_case_if_needed(normalized)

        return {
            "fact_text": template.format(normalized),
            "category": category,
            "confidence": confidence,
            "status": "active",
            "visibility": visibility,
            "is_pinned": is_pinned,
            "provenance": provenance,
            "extraction_pattern": extraction_pattern,
            "durability": durability
        }

    def extract(self, text: str) -> List[Dict]:
        text_clean = text.strip()
        facts = []

        patterns = [
            {
                "pattern": r"\bmy name is ([A-Za-z][A-Za-z0-9_\- ]{1,40})",
                "category": "identity",
                "template": "User's name is {}",
                "confidence": 0.95,
                "pattern_name": "name",
                "durability": "high"
            },
            {
                "pattern": r"\bi live in ([A-Za-z0-9_\- ,']{2,60})",
                "category": "location",
                "template": "User lives in {}",
                "confidence": 0.92,
                "pattern_name": "lives_in",
                "durability": "high"
            },
            {
                "pattern": r"\bi work as ([A-Za-z0-9_\- ,']{2,60})",
                "category": "work",
                "template": "User works as {}",
                "confidence": 0.90,
                "pattern_name": "works_as",
                "durability": "high"
            },
            {
                "pattern": r"\bi work at ([A-Za-z0-9_\- ,']{2,60})",
                "category": "work",
                "template": "User works at {}",
                "confidence": 0.90,
                "pattern_name": "works_at",
                "durability": "medium"
            },
            {
                "pattern": r"\bi am learning ([A-Za-z0-9_\- ,']{2,60})",
                "category": "education",
                "template": "User is learning {}",
                "confidence": 0.88,
                "pattern_name": "learning",
                "durability": "medium"
            },
            {
                "pattern": r"\bi study ([A-Za-z0-9_\- ,']{2,60})",
                "category": "education",
                "template": "User studies {}",
                "confidence": 0.88,
                "pattern_name": "studies",
                "durability": "medium"
            },
            {
                "pattern": r"\bi like ([A-Za-z0-9_\- ,']{2,60})",
                "category": "preference",
                "template": "User likes {}",
                "confidence": 0.82,
                "pattern_name": "likes",
                "durability": "medium"
            },
            {
                "pattern": r"\bi love ([A-Za-z0-9_\- ,']{2,60})",
                "category": "preference",
                "template": "User loves {}",
                "confidence": 0.86,
                "pattern_name": "loves",
                "durability": "medium"
            },
            {
                "pattern": r"\bi prefer ([A-Za-z0-9_\- ,']{2,60})",
                "category": "preference",
                "template": "User prefers {}",
                "confidence": 0.85,
                "pattern_name": "prefers",
                "durability": "medium"
            },
            {
                "pattern": r"\bi am a[n]? ([A-Za-z0-9_\- ,']{2,60})",
                "category": "identity",
                "template": "User is a {}",
                "confidence": 0.84,
                "pattern_name": "identity_role",
                "durability": "medium"
            },
            {
                "pattern": r"\bi'm a[n]? ([A-Za-z0-9_\- ,']{2,60})",
                "category": "identity",
                "template": "User is a {}",
                "confidence": 0.84,
                "pattern_name": "identity_role_contracted",
                "durability": "medium"
            },
        ]

        for item in patterns:
            matches = re.finditer(item["pattern"], text_clean, flags=re.IGNORECASE)
            for match in matches:
                value = self._normalize_value(match.group(1))
                if not value:
                    continue

                if item["category"] == "identity" and item["pattern_name"] in {"identity_role", "identity_role_contracted"}:
                    if self._is_temporary_identity(value):
                        continue

                if item["category"] == "preference":
                    if self._is_low_value_preference(value):
                        continue

                facts.append(
                    self._build_fact(
                        template=item["template"],
                        value=value,
                        category=item["category"],
                        confidence=item["confidence"],
                        extraction_pattern=item["pattern_name"],
                        durability=item["durability"]
                    )
                )

        seen = set()
        unique_facts = []
        for fact in facts:
            key = fact["fact_text"].lower().strip()
            if key not in seen:
                seen.add(key)
                unique_facts.append(fact)

        return unique_facts
