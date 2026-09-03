"""
AetherSAR - backend persistence facade.

Selects the persistence implementation once at startup from the
environment:

  - SUPABASE_URL (http/https) and SUPABASE_KEY both set  -> SupabasePersistence
  - otherwise                                             -> InMemoryPersistence

Routes keep using the single `store` object, so no route contains database
logic and the public API is identical in both modes. Without credentials the
backend runs fully offline on the in-memory store (data lost on restart).
"""

import logging

from backend.database.client import build_client
from backend.database.config import load_config
from backend.database.repositories import InMemoryPersistence, SupabasePersistence

logger = logging.getLogger("aethersar.store")


def create_store():
    config = load_config()
    if config.enabled:
        try:
            client = build_client(config)
        except Exception as exc:
            logger.warning(
                "Supabase is configured but the client could not be created (%s); "
                "falling back to the in-memory store",
                exc,
            )
            return InMemoryPersistence()
        logger.info("AetherSAR persistence: Supabase (%s)", config.supabase_url)
        return SupabasePersistence(client)
    logger.info(
        "AetherSAR persistence: in-memory (set SUPABASE_URL and SUPABASE_KEY "
        "to enable Supabase persistence)"
    )
    return InMemoryPersistence()


store = create_store()


def persistence_mode() -> str:
    """'supabase' when the store persists to Supabase, else 'memory'."""
    return "supabase" if isinstance(store, SupabasePersistence) else "memory"