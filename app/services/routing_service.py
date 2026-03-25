from app.config import settings


class RoutingService:
    """
    Decides which model to use depending on task type.
    This will become smarter later.
    """

    def choose_model(self, user_message: str) -> str:
        text = user_message.lower()

        coding_keywords = [
            "code", "python", "javascript", "bug", "debug", "function",
            "class", "api", "sql", "html", "css", "program", "script"
        ]

        reasoning_keywords = [
            "analyze", "reason", "compare", "plan", "strategy",
            "why", "explain deeply", "step by step", "think"
        ]

        if any(word in text for word in coding_keywords):
            return settings.DEFAULT_CODING_MODEL

        if any(word in text for word in reasoning_keywords):
            return settings.DEFAULT_REASONING_MODEL

        return settings.DEFAULT_CHAT_MODEL
