"""Request-only OpenRouter credentials; never serialize or persist these objects."""
from dataclasses import dataclass, field
from fastapi import Request, HTTPException

FREE_MODEL = "openrouter/free"

@dataclass(frozen=True)
class UserAI:
    key: str = field(repr=False)
    model: str = FREE_MODEL


def user_ai(request: Request) -> UserAI | None:
    key = request.headers.get("x-openrouter-key")
    model = request.headers.get("x-openrouter-model")
    if key is None:
        if model is not None:
            raise HTTPException(400, "An OpenRouter key is required for a user model.")
        return None
    key = key.strip()
    if not key or len(key) > 512 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise HTTPException(400, "Enter a valid OpenRouter key.")
    if model is not None and model != FREE_MODEL:
        raise HTTPException(400, "Only the free OpenRouter router is supported.")
    return UserAI(key)
