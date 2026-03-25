from typing import Dict, List

from app.services.memory_service import MemoryService


class ProfileService:
    def __init__(self):
        self.memory_service = MemoryService()

    def build_profile(self) -> Dict:
        facts = self.memory_service.get_profile_facts()

        profile = {
            "name": None,
            "identity": [],
            "location": [],
            "work": [],
            "preferences": [],
            "education": [],
            "recent_facts": facts[:10],
        }

        for fact in facts:
            text = fact["fact_text"]
            category = fact["category"]

            if "name is" in text.lower() and not profile["name"]:
                profile["name"] = text

            if category == "identity":
                profile["identity"].append(text)
            elif category == "location":
                profile["location"].append(text)
            elif category == "work":
                profile["work"].append(text)
            elif category == "preference":
                profile["preferences"].append(text)
            elif category == "education":
                profile["education"].append(text)

        for key in ["identity", "location", "work", "preferences", "education"]:
            seen = set()
            deduped = []
            for item in profile[key]:
                low = item.lower()
                if low not in seen:
                    seen.add(low)
                    deduped.append(item)
            profile[key] = deduped

        return profile

    def profile_summary_text(self) -> str:
        profile = self.build_profile()

        lines: List[str] = []

        if profile["name"]:
            lines.append(profile["name"])

        for group_name in ["identity", "location", "work", "preferences", "education"]:
            for item in profile[group_name][:5]:
                if item not in lines:
                    lines.append(item)

        if not lines:
            return "No known user facts yet."

        return "\n".join(f"- {line}" for line in lines[:15])
