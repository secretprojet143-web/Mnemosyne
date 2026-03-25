from typing import Callable, Any

from app.config import settings


class JobService:
    """
    Lightweight job abstraction layer.
    Currently supports FastAPI BackgroundTasks mode.
    Future modes can include Celery, RQ, APScheduler, etc.
    """

    def schedule(self, background_tasks, func: Callable[..., Any], *args, **kwargs):
        mode = settings.BACKGROUND_JOB_MODE

        if mode == "fastapi":
            background_tasks.add_task(func, *args, **kwargs)
            return {
                "scheduled": True,
                "mode": "fastapi"
            }

        raise ValueError(f"Unsupported BACKGROUND_JOB_MODE: {mode}")
