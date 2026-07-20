from __future__ import annotations

from dataclasses import dataclass
import secrets
import time


@dataclass(frozen=True)
class AdminSession:
    token: str
    csrf_token: str
    expires_at: int


class AdminSessionManager:
    def __init__(self, *, session_seconds: int) -> None:
        self.session_seconds = session_seconds
        self._sessions: dict[str, AdminSession] = {}

    def create(self) -> AdminSession:
        now = int(time.time())
        session = AdminSession(
            token=secrets.token_urlsafe(32),
            csrf_token=secrets.token_urlsafe(24),
            expires_at=now + self.session_seconds,
        )
        self._sessions[session.token] = session
        self._cleanup(now)
        return session

    def get(self, token: str) -> AdminSession | None:
        now = int(time.time())
        session = self._sessions.get(token)
        if session is None or session.expires_at <= now:
            self._sessions.pop(token, None)
            return None
        return session

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)

    def _cleanup(self, now: int) -> None:
        expired = [token for token, session in self._sessions.items() if session.expires_at <= now]
        for token in expired:
            self._sessions.pop(token, None)


class LoginRateLimiter:
    def __init__(self, *, max_attempts: int = 8, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[int]] = {}

    def allow(self, key: str) -> bool:
        now = int(time.time())
        recent = [item for item in self._attempts.get(key, []) if item > now - self.window_seconds]
        self._attempts[key] = recent
        return len(recent) < self.max_attempts

    def record_failure(self, key: str) -> None:
        self._attempts.setdefault(key, []).append(int(time.time()))

    def clear(self, key: str) -> None:
        self._attempts.pop(key, None)
