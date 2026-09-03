"""
AetherSAR Phase 6 - database configuration.

Supabase persistence is enabled only when BOTH SUPABASE_URL (an http(s)
URL - placeholder text does not enable it) and SUPABASE_KEY are present in
the environment. Otherwise the backend falls back to the in-memory store,
so the project runs fully offline without credentials.
"""

import os
from dataclasses import dataclass

SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_KEY_ENV = "SUPABASE_KEY"


@dataclass(frozen=True)
class DatabaseConfig:
    supabase_url: str
    supabase_key: str
    enabled: bool


def load_config() -> DatabaseConfig:
    """Read configuration from the environment (always fresh, easy to test)."""
    url = os.environ.get(SUPABASE_URL_ENV, "").strip()
    key = os.environ.get(SUPABASE_KEY_ENV, "").strip()
    enabled = bool(url and key and url.startswith(("http://", "https://")))
    return DatabaseConfig(supabase_url=url, supabase_key=key, enabled=enabled)