"""
AetherSAR Phase 6 - persistence repositories.

Two implementations of the same persistence surface:

  InMemoryPersistence  - offline fallback (dict store; data lost on restart)
  SupabasePersistence  - PostgreSQL via the official supabase-py client

API routes talk to a single `store` facade (backend/store.py) that selects
an implementation from the environment at startup, so routes contain no
database logic.

Canonical schema field lists drive the mapping - simulator.telemetry
TELEMETRY_FIELDS and cv.detection DETECTION_FIELDS - so no second telemetry
or detection schema exists here. Detections never carry latitude/longitude:
geolocation is not implemented.

Mission-event logging is deliberately failure-tolerant at the call sites
(see backend/eventlog.py); primary data writes propagate errors instead.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from cv.detection import DETECTION_FIELDS
from simulator.telemetry import TELEMETRY_FIELDS

logger = logging.getLogger("aethersar.persistence")


class PersistenceError(RuntimeError):
    """Raised when a persistence operation fails (e.g. Supabase unavailable)."""


def now_utc_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_timestamp(value):
    """PostgREST returns timestamptz like '...+00:00'; canonical form uses 'Z'."""
    if isinstance(value, str) and value.endswith("+00:00"):
        return value[: -len("+00:00")] + "Z"
    return value


# --------------------------------------------------------------------------
# In-memory implementation (offline fallback)
# --------------------------------------------------------------------------

class InMemoryPersistence:
    """Dict-based persistence. Data is lost on restart - documented."""

    def __init__(self) -> None:
        self._missions: Dict[str, dict] = {}
        self._search_paths: Dict[str, dict] = {}
        self._telemetry: Dict[str, List[dict]] = {}
        self._detections: Dict[str, List[dict]] = {}
        self._search_cells: Dict[str, List[dict]] = {}
        self._mission_events: Dict[str, List[dict]] = {}
        self._drones: Dict[str, dict] = {}
        self._alerts: Dict[str, List[dict]] = {}
        self._media: Dict[str, List[dict]] = {}
        self._reports: Dict[str, List[dict]] = {}

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
        self._drones.setdefault(
            record["drone_id"],
            {
                "id": record["drone_id"],
                "name": record["drone_id"],
                "status": record.get("status", "IDLE"),
                "created_at": now_utc_z(),
                "metadata": {},
            },
        )

    def get_telemetry(self, mission_id: str) -> List[dict]:
        return list(self._telemetry.get(mission_id, []))

    # --- detections -----------------------------------------------------
    def add_detection(self, mission_id: str, record: dict) -> None:
        self._detections.setdefault(mission_id, []).append(record)

    def get_detections(self, mission_id: str) -> List[dict]:
        return list(self._detections.get(mission_id, []))

    # --- search cells ---------------------------------------------------
    def save_search_cells(self, mission_id: str, waypoints: List[dict]) -> int:
        cells = [
            {
                "mission_id": mission_id,
                "cell_index": index,
                "latitude": waypoint["latitude"],
                "longitude": waypoint["longitude"],
                "status": "pending",
                "searched_at": None,
                "metadata": {},
            }
            for index, waypoint in enumerate(waypoints)
        ]
        self._search_cells[mission_id] = cells
        return len(cells)

    def get_search_cells(self, mission_id: str) -> List[dict]:
        return list(self._search_cells.get(mission_id, []))

    # --- mission events -------------------------------------------------
    def add_mission_event(self, mission_id: str, event_type: str, message: str = "", metadata: Optional[dict] = None) -> None:
        event = {
            "id": len(self._mission_events.get(mission_id, [])) + 1,
            "mission_id": mission_id,
            "event_type": event_type,
            "message": message,
            "timestamp": now_utc_z(),
            "metadata": metadata or {},
        }
        self._mission_events.setdefault(mission_id, []).append(event)

    def list_mission_events(self, mission_id: str) -> List[dict]:
        return list(self._mission_events.get(mission_id, []))

    # --- drones ---------------------------------------------------------
    def ensure_drone(self, drone_id: str, status: str = "IDLE") -> None:
        if drone_id in self._drones:
            return
        self._drones[drone_id] = {
            "id": drone_id,
            "name": drone_id,
            "status": status,
            "created_at": now_utc_z(),
            "metadata": {},
        }

    def list_drones(self) -> List[dict]:
        return list(self._drones.values())

    # --- alerts ---------------------------------------------------------
    def add_alert(
        self,
        mission_id: str,
        *,
        severity: str,
        title: str,
        message: str = "",
        detection_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        alert = {
            "id": uuid4().hex,
            "mission_id": mission_id,
            "detection_id": detection_id,
            "severity": severity,
            "title": title,
            "message": message,
            "status": "open",
            "created_at": now_utc_z(),
            "acknowledged_at": None,
            "metadata": metadata or {},
        }
        self._alerts.setdefault(mission_id, []).append(alert)
        return dict(alert)

    def list_alerts(self, mission_id: str) -> List[dict]:
        return list(self._alerts.get(mission_id, []))

    # --- media ----------------------------------------------------------
    def add_media(
        self,
        mission_id: str,
        *,
        media_type: str,
        storage_path: str,
        detection_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        media = {
            "id": uuid4().hex,
            "mission_id": mission_id,
            "detection_id": detection_id,
            "media_type": media_type,
            "storage_path": storage_path,
            "created_at": now_utc_z(),
            "metadata": metadata or {},
        }
        self._media.setdefault(mission_id, []).append(media)
        return dict(media)

    def list_media(self, mission_id: str) -> List[dict]:
        return list(self._media.get(mission_id, []))

    # --- reports --------------------------------------------------------
    def add_report(
        self,
        mission_id: str,
        *,
        report_type: str = "mission",
        status: str = "pending",
        storage_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        report = {
            "id": uuid4().hex,
            "mission_id": mission_id,
            "report_type": report_type,
            "status": status,
            "storage_path": storage_path,
            "created_at": now_utc_z(),
            "metadata": metadata or {},
        }
        self._reports.setdefault(mission_id, []).append(report)
        return dict(report)

    def list_reports(self, mission_id: str) -> List[dict]:
        return list(self._reports.get(mission_id, []))


# --------------------------------------------------------------------------
# Supabase implementation
# --------------------------------------------------------------------------

class SupabasePersistence:
    """PostgreSQL persistence through the official supabase-py client.

    Expects a client already constructed with a service-role key
    (backend/database/client.py). Multi-row sequences are not wrapped in a
    single transaction - acceptable for the prototype.
    """

    def __init__(self, client) -> None:
        self._client = client
        self._known_drones = set()

    # --- low-level helpers ----------------------------------------------
    def _table(self, name: str):
        return self._client.table(name)

    def _run(self, operation: str, query) -> List[dict]:
        try:
            result = query.execute()
        except Exception as exc:
            raise PersistenceError(f"supabase {operation} failed: {exc}") from exc
        return result.data or []

    # --- missions -------------------------------------------------------
    def add_mission(self, mission: dict) -> None:
        row = {
            "id": mission["mission_id"],
            "name": mission["name"],
            "status": mission["status"],
            "search_area": mission["search_area"],
            "created_at": mission["created_at"],
            "metadata": mission.get("metadata", {}),
        }
        self._run("insert mission", self._table("missions").insert(row))

    def get_mission(self, mission_id: str) -> Optional[dict]:
        rows = self._run(
            "select mission", self._table("missions").select("*").eq("id", mission_id)
        )
        return self._mission_from_row(rows[0]) if rows else None

    def mission_exists(self, mission_id: str) -> bool:
        return self.get_mission(mission_id) is not None

    def _mission_from_row(self, row: dict) -> dict:
        return {
            "mission_id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "search_area": row["search_area"],
            "created_at": _normalize_timestamp(row["created_at"]),
        }

    # --- search paths ---------------------------------------------------
    def set_search_path(self, mission_id: str, path: dict) -> None:
        row = {
            "mission_id": mission_id,
            "spacing_m": path["spacing_m"],
            "waypoints": path["waypoints"],
            "generated_at": path["generated_at"],
        }
        self._run(
            "upsert search path",
            self._table("search_paths").upsert(row, on_conflict="mission_id"),
        )

    def get_search_path(self, mission_id: str) -> Optional[dict]:
        rows = self._run(
            "select search path",
            self._table("search_paths").select("*").eq("mission_id", mission_id),
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "mission_id": row["mission_id"],
            "spacing_m": row["spacing_m"],
            "waypoints": row["waypoints"],
            "generated_at": _normalize_timestamp(row["generated_at"]),
        }

    # --- telemetry ------------------------------------------------------
    def add_telemetry(self, mission_id: str, record: dict) -> None:
        self._ensure_drone(record["drone_id"], status=record.get("status", "IDLE"))
        row = dict(record)  # canonical keys match the telemetry columns exactly
        self._run("insert telemetry", self._table("telemetry").insert(row))

    def get_telemetry(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select telemetry",
            self._table("telemetry")
            .select("*")
            .eq("mission_id", mission_id)
            .order("id"),
        )
        return [self._telemetry_from_row(row) for row in rows]

    def _telemetry_from_row(self, row: dict) -> dict:
        return {key: _normalize_timestamp(row[key]) if key == "timestamp" else row[key]
                for key in TELEMETRY_FIELDS}

    # --- detections -----------------------------------------------------
    def add_detection(self, mission_id: str, record: dict) -> None:
        row = dict(record)
        row["mission_id"] = mission_id  # association lives at the row level only
        self._run("insert detection", self._table("detections").insert(row))

    def get_detections(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select detections",
            self._table("detections")
            .select("*")
            .eq("mission_id", mission_id)
            .order("id"),
        )
        return [self._detection_from_row(row) for row in rows]

    def _detection_from_row(self, row: dict) -> dict:
        return {key: _normalize_timestamp(row[key]) if key == "timestamp" else row[key]
                for key in DETECTION_FIELDS}

    # --- search cells ---------------------------------------------------
    def save_search_cells(self, mission_id: str, waypoints: List[dict]) -> int:
        # Regenerate: clear previous cells for the mission, then insert.
        self._run(
            "delete search cells",
            self._table("search_cells").delete().eq("mission_id", mission_id),
        )
        if not waypoints:
            return 0
        rows = [
            {
                "mission_id": mission_id,
                "cell_index": index,
                "latitude": waypoint["latitude"],
                "longitude": waypoint["longitude"],
                "status": "pending",
                "searched_at": None,
                "metadata": {},
            }
            for index, waypoint in enumerate(waypoints)
        ]
        self._run("insert search cells", self._table("search_cells").insert(rows))
        return len(rows)

    def get_search_cells(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select search cells",
            self._table("search_cells")
            .select("*")
            .eq("mission_id", mission_id)
            .order("cell_index"),
        )
        for row in rows:
            row["searched_at"] = _normalize_timestamp(row["searched_at"]) if row.get("searched_at") else None
        return rows

    # --- mission events -------------------------------------------------
    def add_mission_event(self, mission_id: str, event_type: str, message: str = "", metadata: Optional[dict] = None) -> None:
        row = {
            "mission_id": mission_id,
            "event_type": event_type,
            "message": message,
            "timestamp": now_utc_z(),
            "metadata": metadata or {},
        }
        self._run("insert mission event", self._table("mission_events").insert(row))

    def list_mission_events(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select mission events",
            self._table("mission_events")
            .select("*")
            .eq("mission_id", mission_id)
            .order("id"),
        )
        for row in rows:
            row["timestamp"] = _normalize_timestamp(row["timestamp"])
        return rows

    # --- drones ---------------------------------------------------------
    def _ensure_drone(self, drone_id: str, status: str = "IDLE") -> None:
        if drone_id in self._known_drones:
            return
        row = {
            "id": drone_id,
            "name": drone_id,
            "status": status,
            "created_at": now_utc_z(),
            "metadata": {},
        }
        self._run("upsert drone", self._table("drones").upsert(row, on_conflict="id"))
        self._known_drones.add(drone_id)

    def ensure_drone(self, drone_id: str, status: str = "IDLE") -> None:
        self._ensure_drone(drone_id, status=status)

    def list_drones(self) -> List[dict]:
        rows = self._run("select drones", self._table("drones").select("*").order("id"))
        for row in rows:
            row["created_at"] = _normalize_timestamp(row["created_at"])
        return rows

    # --- alerts ---------------------------------------------------------
    def add_alert(
        self,
        mission_id: str,
        *,
        severity: str,
        title: str,
        message: str = "",
        detection_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        row = {
            "id": uuid4().hex,
            "mission_id": mission_id,
            "detection_id": detection_id,
            "severity": severity,
            "title": title,
            "message": message,
            "status": "open",
            "created_at": now_utc_z(),
            "acknowledged_at": None,
            "metadata": metadata or {},
        }
        self._run("insert alert", self._table("alerts").insert(row))
        return self._alert_from_row(row)

    def list_alerts(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select alerts",
            self._table("alerts").select("*").eq("mission_id", mission_id).order("id"),
        )
        return [self._alert_from_row(row) for row in rows]

    def _alert_from_row(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "mission_id": row["mission_id"],
            "detection_id": row.get("detection_id"),
            "severity": row["severity"],
            "title": row["title"],
            "message": row["message"],
            "status": row["status"],
            "created_at": _normalize_timestamp(row["created_at"]),
            "acknowledged_at": _normalize_timestamp(row["acknowledged_at"])
            if row.get("acknowledged_at")
            else None,
            "metadata": row["metadata"],
        }

    # --- media ----------------------------------------------------------
    def add_media(
        self,
        mission_id: str,
        *,
        media_type: str,
        storage_path: str,
        detection_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        row = {
            "id": uuid4().hex,
            "mission_id": mission_id,
            "detection_id": detection_id,
            "media_type": media_type,
            "storage_path": storage_path,
            "created_at": now_utc_z(),
            "metadata": metadata or {},
        }
        self._run("insert media", self._table("media").insert(row))
        return self._media_from_row(row)

    def list_media(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select media",
            self._table("media").select("*").eq("mission_id", mission_id).order("id"),
        )
        return [self._media_from_row(row) for row in rows]

    def _media_from_row(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "mission_id": row["mission_id"],
            "detection_id": row.get("detection_id"),
            "media_type": row["media_type"],
            "storage_path": row["storage_path"],
            "created_at": _normalize_timestamp(row["created_at"]),
            "metadata": row["metadata"],
        }

    # --- reports --------------------------------------------------------
    def add_report(
        self,
        mission_id: str,
        *,
        report_type: str = "mission",
        status: str = "pending",
        storage_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        row = {
            "id": uuid4().hex,
            "mission_id": mission_id,
            "report_type": report_type,
            "status": status,
            "storage_path": storage_path,
            "created_at": now_utc_z(),
            "metadata": metadata or {},
        }
        self._run("insert report", self._table("reports").insert(row))
        return self._report_from_row(row)

    def list_reports(self, mission_id: str) -> List[dict]:
        rows = self._run(
            "select reports",
            self._table("reports").select("*").eq("mission_id", mission_id).order("id"),
        )
        return [self._report_from_row(row) for row in rows]

    def _report_from_row(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "mission_id": row["mission_id"],
            "report_type": row["report_type"],
            "status": row["status"],
            "storage_path": row.get("storage_path"),
            "created_at": _normalize_timestamp(row["created_at"]),
            "metadata": row["metadata"],
        }