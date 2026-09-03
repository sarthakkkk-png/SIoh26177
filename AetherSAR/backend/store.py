"""
AetherSAR Phase 5 - in-memory store.

Deliberately no database: a simple dict store is enough for the local
prototype and requires no external infrastructure. Data is lost on
restart - documented in README.md.
"""

from typing import Dict, List, Optional


class InMemoryStore:
    def __init__(self) -> None:
        self._missions: Dict[str, dict] = {}
        self._search_paths: Dict[str, dict] = {}
        self._telemetry: Dict[str, List[dict]] = {}
        self._detections: Dict[str, List[dict]] = {}

    # --- missions -------------------------------------------------------
    def add_mission(self, mission: dict) -> None:
        self._missions[mission["mission_id"]] = mission

    def get_mission(self, mission_id: str) -> Optional[dict]:
        return self._missions.get(mission_id)

    def mission_exists(self, mission_id: str) -> bool:
        return mission_id in self._missions

    # --- search paths ---------------------------------------------------
    def set_search_path(self, mission_id: str, path: dict) -> None:
        self._search_paths[mission_id] = path

    def get_search_path(self, mission_id: str) -> Optional[dict]:
        return self._search_paths.get(mission_id)

    # --- telemetry ------------------------------------------------------
    def add_telemetry(self, mission_id: str, record: dict) -> None:
        self._telemetry.setdefault(mission_id, []).append(record)

    def get_telemetry(self, mission_id: str) -> List[dict]:
        return list(self._telemetry.get(mission_id, []))

    # --- detections -----------------------------------------------------
    def add_detection(self, mission_id: str, record: dict) -> None:
        self._detections.setdefault(mission_id, []).append(record)

    def get_detections(self, mission_id: str) -> List[dict]:
        return list(self._detections.get(mission_id, []))


store = InMemoryStore()