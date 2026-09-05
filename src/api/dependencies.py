"""
In-Memory Session Store for Runtime Key Override (NexusTiq24 PS06).
Kept in memory only — NEVER logged, NEVER written to disk, NEVER committed.
"""

from typing import Optional


class SessionStore:
    def __init__(self):
        self._api_key_override: Optional[str] = None

    def set_key(self, api_key: str):
        self._api_key_override = api_key.strip() if api_key else None

    def get_key(self) -> Optional[str]:
        return self._api_key_override

    def clear_key(self):
        self._api_key_override = None


session_store = SessionStore()
