import re
from typing import Dict, List


class ContinuityExtractor:
    def extract(self, text: str) -> Dict[str, List[Dict]]:
        text_clean = text.strip()
        lowered = text_clean.lower()

        projects = []
        goals = []
        open_loops = []

        project_patterns = [
            r"\bi(?:'m| am)?\s+(?:building|creating|developing|working on)\s+(.+)",
            r"\bmy project is\s+(.+)",
            r"\bi'm making\s+(.+)",
        ]

        for pattern in project_patterns:
            matches = re.finditer(pattern, lowered, flags=re.IGNORECASE)
            for match in matches:
                value = match.group(1).strip(" .,!?:;")
                if value and len(value) >= 4:
                    projects.append({
                        "title": self._clean_phrase(value),
                        "description": text_clean,
                        "confidence": 0.82,
                        "source_type": "heuristic_project"
                    })

        goal_patterns = [
            r"\bi want to\s+(.+)",
            r"\bmy goal is to\s+(.+)",
            r"\bi need to\s+(.+)",
            r"\bi'm trying to\s+(.+)",
            r"\bi plan to\s+(.+)"
        ]

        for pattern in goal_patterns:
            matches = re.finditer(pattern, lowered, flags=re.IGNORECASE)
            for match in matches:
                value = match.group(1).strip(" .,!?:;")
                if value and len(value) >= 4:
                    goals.append({
                        "goal_text": self._clean_phrase(value),
                        "confidence": 0.80,
                        "source_type": "heuristic_goal"
                    })

        open_loop_patterns = [
            r"\bwe still need to\s+(.+)",
            r"\bi still need to\s+(.+)",
            r"\bneed to\s+(.+)",
            r"\bi haven't decided\s+(.+)",
            r"\bi have not decided\s+(.+)",
            r"\bthere is a bug in\s+(.+)",
            r"\bthere's a bug in\s+(.+)",
            r"\bthe problem is\s+(.+)",
            r"\bwe need to figure out\s+(.+)"
        ]

        for pattern in open_loop_patterns:
            matches = re.finditer(pattern, lowered, flags=re.IGNORECASE)
            for match in matches:
                value = match.group(1).strip(" .,!?:;")
                if value and len(value) >= 4:
                    open_loops.append({
                        "description": self._clean_phrase(value),
                        "confidence": 0.84,
                        "source_type": "heuristic_open_loop"
                    })

        return {
            "projects": self._dedupe_items(projects, key="title"),
            "goals": self._dedupe_items(goals, key="goal_text"),
            "open_loops": self._dedupe_items(open_loops, key="description")
        }

    def _clean_phrase(self, text: str) -> str:
        text = text.strip(" .,!?:;")
        text = re.sub(r"\s+", " ", text)
        return text[:120].strip()

    def _dedupe_items(self, items: List[Dict], key: str) -> List[Dict]:
        seen = set()
        deduped = []

        for item in items:
            value = item.get(key, "").strip().lower()
            if value and value not in seen:
                seen.add(value)
                deduped.append(item)

        return deduped
