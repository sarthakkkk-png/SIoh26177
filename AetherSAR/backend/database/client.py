"""
AetherSAR Phase 6 - Supabase client construction.

The official 'supabase' package is imported lazily so the rest of the
backend (and the offline test suite) works without it installed.
"""

from typing import Any, Optional

from backend.database.config import DatabaseConfig, load_config

_client_cache: Optional[Any] = None


class DatabaseNotConfigured(RuntimeError):
    """Raised when Supabase usage is requested without valid configuration."""


def build_client(config: Optional[DatabaseConfig] = None) -> Any:
    """Create a Supabase client for the given (or environment) configuration."""
    cfg = config if config is not None else load_config()
    if not cfg.enabled:
        raise DatabaseNotConfigured(
            "Supabase is not configured; set SUPABASE_URL and SUPABASE_KEY"
        )
    try:
        from supabase import create_client
    except ImportError as exc:
        raise DatabaseNotConfigured(
            "the 'supabase' package is not installed; "
            "run 'pip install -r backend/requirements.txt'"
        ) from exc
    return create_client(cfg.supabase_url, cfg.supabase_key)


def get_client() -> Any:
    """Return a cached Supabase client, or None when not configured."""
    global _client_cache
    if _client_cache is None:
        config = load_config()
        if not config.enabled:
            return None
        _client_cache = build_client(config)
    return _client_cache


def reset_client_cache() -> None:
    global _client_cache
    _client_cache = None