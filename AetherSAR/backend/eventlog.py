"""
AetherSAR - mission event log helper.

Mission events (MISSION_CREATED, SEARCH_PATH_GENERATED, DETECTION_RECEIVED,
...) are a secondary audit trail: primary data writes must never be blocked
by an event-log failure, so failures here are logged to the server console
and do not fail the request.
"""

import logging

from backend.store import store

logger = logging.getLogger("aethersar.eventlog")


def record_event(mission_id: str, event_type: str, message: str = "") -> None:
    try:
        store.add_mission_event(mission_id, event_type, message)
    except Exception:
        logger.exception(
            "failed to record mission event %s for mission %s", event_type, mission_id
        )