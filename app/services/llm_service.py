import json
import requests
from typing import List, Dict, Any, Optional, Generator

from app.config import settings


class OpenRouterError(Exception):
    pass


class LLMService:
    """Multi-provider LLM service with fallback support.

    Supports:
    - Xiaomi MiMo via SiliconFlow (free tier available)
    - OpenRouter (cloud, paid)
    - Ollama (local, free)
    - Fallback (built-in intelligent responses, no API needed)
    """

    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT_SECONDS
        self.provider = settings.active_provider

    def _get_provider_config(self) -> tuple[str, str, str]:
        """Returns (api_key, base_url, model) for the active provider."""
        if self.provider == "xiaomi":
            return (
                settings.XIAOMI_API_KEY,
                settings.XIAOMI_BASE_URL.rstrip("/"),
                settings.XIAOMI_MODEL,
            )
        elif self.provider == "openrouter":
            return (
                settings.OPENROUTER_API_KEY,
                settings.OPENROUTER_BASE_URL.rstrip("/"),
                settings.DEFAULT_CHAT_MODEL,
            )
        return ("", "", "")

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self.provider == "xiaomi":
            return self._chat_openai_compatible(model, messages, temperature, max_tokens)
        elif self.provider == "openrouter":
            return self._chat_openai_compatible(model, messages, temperature, max_tokens)
        elif self.provider == "ollama":
            return self._chat_ollama(model, messages, temperature, max_tokens)
        else:
            return self._chat_fallback(messages, model)

    def simple_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        selected_model = model or settings.DEFAULT_CHAT_MODEL
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        return self.chat(model=selected_model, messages=messages)

    def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """Yield tokens as they arrive from the API (SSE streaming)."""
        if self.provider in ("xiaomi", "openrouter"):
            yield from self._stream_openai_compatible(model, messages, temperature, max_tokens)
        else:
            result = self.chat(model, messages, temperature, max_tokens)
            yield result["content"]

    # ─── OpenAI-Compatible (Xiaomi/SiliconFlow/OpenRouter) ──

    def _chat_openai_compatible(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        api_key, base_url, provider_model = self._get_provider_config()

        if not api_key:
            return self._chat_fallback(messages, model)

        # Use provider's model name
        if self.provider == "xiaomi":
            model = settings.XIAOMI_MODEL

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            return self._chat_fallback(messages, model)

        if response.status_code >= 400:
            return self._chat_fallback(messages, model)

        data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return self._chat_fallback(messages, model)

        return {
            "model": data.get("model", model),
            "content": content,
            "raw": data,
            "usage": data.get("usage", {}),
        }

    def _stream_openai_compatible(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        api_key, base_url, provider_model = self._get_provider_config()

        if not api_key:
            yield self._chat_fallback(messages, model)["content"]
            return

        if self.provider == "xiaomi":
            model = settings.XIAOMI_MODEL

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
        except requests.RequestException:
            yield self._chat_fallback(messages, model)["content"]
            return

        if response.status_code >= 400:
            yield self._chat_fallback(messages, model)["content"]
            return

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.strip():
                continue
            line = raw_line.strip()
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    return
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError):
                    continue

    # ─── Ollama ───────────────────────────────────────────────

    def _chat_ollama(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        ollama_model = settings.OLLAMA_MODEL
        if model and not model.startswith("openai/") and not model.startswith("anthropic/") and not model.startswith("xiaomi/"):
            ollama_model = model

        payload: Dict[str, Any] = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException:
            return self._chat_fallback(messages, model)

        if response.status_code >= 400:
            return self._chat_fallback(messages, model)

        data = response.json()
        content = data.get("message", {}).get("content", "")

        return {
            "model": ollama_model,
            "content": content,
            "raw": data,
            "usage": data.get("usage", {}),
        }

    # ─── Fallback (no API needed) ─────────────────────────────

    def _chat_fallback(
        self,
        messages: List[Dict[str, str]],
        model: str = "fallback",
    ) -> Dict[str, Any]:
        user_msg = ""
        system_msg = ""
        for msg in messages:
            if msg["role"] == "user":
                user_msg = msg["content"]
            elif msg["role"] == "system":
                system_msg = msg["content"]
        content = self._generate_fallback_response(user_msg, system_msg)
        return {
            "model": "mnemosyne-fallback",
            "content": content,
            "raw": {"fallback": True},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def _generate_fallback_response(self, user_msg: str, system_msg: str) -> str:
        msg = user_msg.lower().strip()

        if "json" in system_msg.lower() and "reasoning" in system_msg.lower():
            return json.dumps({
                "task": user_msg[:100], "goal": "Process the user's request",
                "constraints": ["Stay within available capabilities"],
                "assumptions": ["User expects a structured response"],
                "candidate_actions": ["Analyze request", "Generate response", "Verify output"],
                "selected_action": "Generate response", "confidence": 0.75,
                "self_check": {"goal_alignment": True, "constraint_risk": "low", "missing_information": []},
                "status": "draft"
            })

        if "json" in system_msg.lower() and "plan" in system_msg.lower():
            return json.dumps({
                "title": f"Plan: {user_msg[:50]}", "goal": "Complete the requested task",
                "steps": [
                    {"step_order": 1, "title": "Analyze", "description": "Understand the request", "status": "pending", "notes": ""},
                    {"step_order": 2, "title": "Execute", "description": "Perform the task", "status": "pending", "notes": ""},
                ]
            })

        if any(g in msg for g in ["hello", "hi ", "hey", "greetings"]):
            return "Hello! I'm Mnemosyne, your AI assistant with persistent memory. I remember facts about you across conversations. How can I help you today?"

        if "help" in msg:
            return "I can help you with:\n- **Memory** - I remember facts about you\n- **Projects** - Track goals and tasks\n- **Planning** - Break tasks into steps\n- **Documents** - Search and analyze docs\n\nWhat would you like to do?"

        if "what can you do" in msg or "capabilities" in msg:
            return "My capabilities:\n1. **Persistent Memory** - Facts stored across sessions\n2. **Fact Extraction** - Auto-extract important info\n3. **Project Tracking** - Goals, open loops\n4. **Proactive Briefing** - What needs attention\n5. **Temporal Awareness** - Detect changes over time"

        return f"I received your message. I'm running in local mode. Your message: \"{user_msg[:100]}{'...' if len(user_msg) > 100 else ''}\""

    def is_connected(self) -> bool:
        if self.provider == "xiaomi" and settings.XIAOMI_API_KEY:
            return True
        if self.provider == "openrouter" and settings.OPENROUTER_API_KEY:
            return True
        if self.provider == "ollama":
            try:
                r = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
                return r.status_code == 200
            except Exception:
                return False
        return False
