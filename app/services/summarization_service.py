import json
import re
from typing import List, Dict

from app.config import settings
from app.services.llm_service import LLMService


class SummarizationService:
    def __init__(self):
        self.llm_service = LLMService()

    def summarize_conversation(self, messages: List[Dict]) -> str:
        if not messages:
            return "No conversation content available."

        transcript = self._build_transcript(messages)

        prompt = (
            "Summarize this conversation into a compact episodic memory. "
            "Focus on:\n"
            "- important user goals\n"
            "- important preferences\n"
            "- key project details\n"
            "- unresolved issues\n"
            "- major decisions\n\n"
            "Keep it concise but useful."
        )

        result = self.llm_service.chat(
            model=settings.DEFAULT_SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": "You create concise memory summaries for an evolving AI assistant."},
                {"role": "user", "content": f"{prompt}\n\nConversation:\n{transcript}"}
            ],
            temperature=0.3
        )

        return result["content"].strip()

    def generate_reflection(self, messages: List[Dict]) -> str:
        structured = self.generate_structured_reflection(messages)
        return structured["reflection_text"]

    def generate_structured_reflection(self, messages: List[Dict]) -> Dict:
        if not messages:
            return self._empty_reflection("No reflection available.")

        transcript = self._build_transcript(messages)

        prompt = (
            "You are generating a structured reflection for Mnemosyne AI.\n"
            "Analyze the conversation and return ONLY valid JSON.\n\n"
            "Focus only on durable, actionable, memory-relevant insights.\n"
            "Avoid vague personality commentary.\n"
            "Do not include anything temporary or trivial unless it matters for future continuity.\n\n"
            "Return JSON with exactly these keys:\n"
            "{\n"
            '  "reflection_text": string,\n'
            '  "reflection_type": string,\n'
            '  "user_insights": [string],\n'
            '  "preference_updates": [string],\n'
            '  "project_updates": [string],\n'
            '  "goal_updates": [string],\n'
            '  "potential_conflicts": [string],\n'
            '  "recommended_long_term_memories": [string]\n'
            "}\n\n"
            "Guidelines:\n"
            "- reflection_text should be concise, practical, and grounded in the conversation.\n"
            "- user_insights should capture durable user values, priorities, or patterns.\n"
            "- preference_updates should capture stable communication or product preferences.\n"
            "- project_updates should capture movement in ongoing projects.\n"
            "- goal_updates should capture active or emerging goals.\n"
            "- potential_conflicts should note ambiguity, contradiction, or uncertainty.\n"
            "- recommended_long_term_memories should contain only things worth remembering later.\n"
            "- reflection_type should be 'conversation_reflection'.\n"
            "- If a category has nothing important, return an empty array.\n"
            "- Return JSON only. No markdown. No code block."
        )

        try:
            result = self.llm_service.chat(
                model=settings.DEFAULT_SUMMARY_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate structured reflections for an evolving AI memory system. "
                            "Return only valid JSON."
                        )
                    },
                    {"role": "user", "content": f"{prompt}\n\nConversation:\n{transcript}"}
                ],
                temperature=0.3
            )

            raw = result["content"].strip()
            parsed = self._parse_json_response(raw)
            return self._normalize_reflection(parsed)

        except Exception:
            fallback_text = self._generate_plain_reflection_fallback(transcript)
            return self._empty_reflection(fallback_text)

    def _generate_plain_reflection_fallback(self, transcript: str) -> str:
        prompt = (
            "Reflect on this conversation as Mnemosyne AI.\n"
            "Write a short reflection about:\n"
            "- what the user seems to care about\n"
            "- what should be remembered later\n"
            "- what follow-up may help in future\n"
            "- what was learned from this interaction\n\n"
            "Be concise and practical."
        )

        try:
            result = self.llm_service.chat(
                model=settings.DEFAULT_SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You generate reflection notes for an evolving AI memory system."},
                    {"role": "user", "content": f"{prompt}\n\nConversation:\n{transcript}"}
                ],
                temperature=0.4
            )
            return result["content"].strip()
        except Exception:
            return "Reflection generation failed, but the conversation may still contain useful long-term signals."

    def _build_transcript(self, messages: List[Dict]) -> str:
        transcript_parts = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "").strip()
            if content:
                transcript_parts.append(f"{role}: {content}")
        return "\n".join(transcript_parts[-30:])

    def _parse_json_response(self, raw: str) -> Dict:
        raw = raw.strip()

        try:
            return json.loads(raw)
        except Exception:
            pass

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))

        raise ValueError("Could not parse structured reflection JSON.")

    def _normalize_reflection(self, data: Dict) -> Dict:
        def ensure_list(value):
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]
            return []

        reflection_text = str(data.get("reflection_text", "")).strip()
        if not reflection_text:
            reflection_text = "No substantial reflection generated."

        reflection_type = str(data.get("reflection_type", "conversation_reflection")).strip() or "conversation_reflection"

        return {
            "reflection_text": reflection_text,
            "reflection_type": reflection_type,
            "user_insights": ensure_list(data.get("user_insights")),
            "preference_updates": ensure_list(data.get("preference_updates")),
            "project_updates": ensure_list(data.get("project_updates")),
            "goal_updates": ensure_list(data.get("goal_updates")),
            "potential_conflicts": ensure_list(data.get("potential_conflicts")),
            "recommended_long_term_memories": ensure_list(data.get("recommended_long_term_memories"))
        }

    def _empty_reflection(self, reflection_text: str) -> Dict:
        return {
            "reflection_text": reflection_text.strip() if reflection_text else "No reflection available.",
            "reflection_type": "conversation_reflection",
            "user_insights": [],
            "preference_updates": [],
            "project_updates": [],
            "goal_updates": [],
            "potential_conflicts": [],
            "recommended_long_term_memories": []
        }
