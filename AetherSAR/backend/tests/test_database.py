"""
AetherSAR Phase 6 - database/persistence tests.

Offline-safe: no real Supabase account or credentials are required.
Covers configuration, the in-memory fallback, and the Supabase repository
logic against a fake postgREST-style client, plus search-cell/event/alert
abstractions and canonical-schema integrity.

Run: python3 -m backend.tests.test_database
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database.config import SUPABASE_KEY_ENV, SUPABASE_URL_ENV, load_config
from backend.database.repositories import (
    InMemoryPersistence,
    PersistenceError,
    SupabasePersistence,
)
from backend.store import create_store, persistence_mode, store
from cv.detection import DETECTION_FIELDS
from simulator.telemetry import TELEMETRY_FIELDS


# --------------------------------------------------------------------------
# Fake postgREST-style client (records rows per table, honors the queries
# the repositories actually issue: insert/upsert/select/eq/order/delete).
# --------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, table_name, db):
        self._table = table_name
        self._db = db
        self._rows_to_insert = None
        self._upsert = None
        self._on_conflict = None
        self._eq = None
        self._order = None
        self._delete = False

    def insert(self, rows):
        self._rows_to_insert = rows if isinstance(rows, list) else [rows]
        return self

    def upsert(self, rows, on_conflict=None):
        self._upsert = rows if isinstance(rows, list) else [rows]
        self._on_conflict = on_conflict
        return self

    def select(self, *_cols):
        return self

    def delete(self):
        self._delete = True
        return self

    def eq(self, column, value):
        self._eq = (column, value)
        return self

    def order(self, column, desc=False):
        self._order = (column, desc)
        return self

    def execute(self):
        table_rows = self._db.setdefault(self._table, [])
        if self._rows_to_insert is not None:
            table_rows.extend(self._rows_to_insert)
            return _FakeResult(list(self._rows_to_insert))
        if self._upsert is not None:
            for row in self._upsert:
                if self._on_conflict:
                    replaced = False
                    for existing in table_rows:
                        if all(existing.get(k) == row.get(k) for k in self._on_conflict.split(",")):
                            existing.update(row)
                            replaced = True
                            break
                    if not replaced:
                        table_rows.append(row)
                else:
                    table_rows.append(row)
            return _FakeResult(list(self._upsert))
        rows = table_rows
        if self._eq:
            column, value = self._eq
            rows = [r for r in rows if r.get(column) == value]
        if self._delete:
            removed = len(rows)
            table_rows[:] = [r for r in table_rows if r not in rows]
            return _FakeResult([])
        if self._order:
            column, desc = self._order
            if rows and all(column in r for r in rows):
                rows = sorted(rows, key=lambda r: r[column], reverse=desc)
        return _FakeResult([dict(r) for r in rows])


class FakeSupabase:
    def __init__(self):
        self.db = {}

    def table(self, name):
        return _FakeQuery(name, self.db)


def _fake_client():
    return FakeSupabase()


def _mission_dict(mission_id="m1"):
    return {
        "mission_id": mission_id,
        "name": "Test mission",
        "status": "created",
        "search_area": {"min_lat": 18.5204, "min_lon": 73.8567, "max_lat": 18.5228, "max_lon": 73.8599},
        "created_at": "2026-09-03T16:53:43.235Z",
    }


def _telemetry_dict(mission_id="m1", drone_id="DRONE-01"):
    return {
        "drone_id": drone_id,
        "mission_id": mission_id,
        "timestamp": "2026-09-03T16:53:43.235Z",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "altitude_m": 80.0,
        "heading_deg": 90.0,
        "speed_mps": 8.0,
        "battery_pct": 95.0,
        "status": "SEARCHING",
        "current_waypoint": 1,
        "total_waypoints": 25,
        "source": "SIMULATED",
    }


def _detection_dict():
    return {
        "timestamp": "2026-09-03T16:53:43.235Z",
        "drone_id": "DRONE-01",
        "frame_id": 42,
        "class": "person",
        "confidence": 0.87,
        "bbox": {"x1": 120, "y1": 80, "x2": 250, "y2": 310},
    }


# --------------------------------------------------------------------------
# Configuration + fallback
# --------------------------------------------------------------------------

def test_config_defaults_disabled():
    saved = {key: os.environ.pop(key, None) for key in (SUPABASE_URL_ENV, SUPABASE_KEY_ENV)}
    try:
        config = load_config()
        assert config.enabled is False
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
    print("PASS: no credentials -> Supabase disabled")


def test_config_enabled_with_credentials():
    saved = {key: os.environ.pop(key, None) for key in (SUPABASE_URL_ENV, SUPABASE_KEY_ENV)}
    try:
        os.environ[SUPABASE_URL_ENV] = "https://demo.supabase.co"
        os.environ[SUPABASE_KEY_ENV] = "test-key"
        config = load_config()
        assert config.enabled is True
        assert config.supabase_url == "https://demo.supabase.co"
        assert config.supabase_key == "test-key"
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
    print("PASS: credentials present -> Supabase enabled")


def test_placeholder_url_does_not_enable():
    saved = {key: os.environ.pop(key, None) for key in (SUPABASE_URL_ENV, SUPABASE_KEY_ENV)}
    try:
        os.environ[SUPABASE_URL_ENV] = "your-project-ref.supabase.co"  # not an http URL
        os.environ[SUPABASE_KEY_ENV] = "x"
        assert load_config().enabled is False
        os.environ[SUPABASE_URL_ENV] = "https://your-project-ref.supabase.co"
        os.environ[SUPABASE_KEY_ENV] = ""
        assert load_config().enabled is False
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
    print("PASS: non-http or missing values keep persistence disabled")


def test_fallback_store_is_in_memory():
    # The normal test environment has no Supabase credentials, so the
    # startup store must be the in-memory implementation.
    assert persistence_mode() == "memory"
    assert isinstance(store, InMemoryPersistence)
    print("PASS: backend store falls back to in-memory without credentials")


def test_create_store_selects_supabase_when_configured():
    saved = {key: os.environ.pop(key, None) for key in (SUPABASE_URL_ENV, SUPABASE_KEY_ENV)}
    try:
        os.environ[SUPABASE_URL_ENV] = "https://demo.supabase.co"
        os.environ[SUPABASE_KEY_ENV] = "test-key"
        # create_store() builds a client locally (no network at construction)
        # and must select the Supabase implementation.
        configured_store = create_store()
        assert isinstance(configured_store, SupabasePersistence)
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
    print("PASS: create_store selects Supabase persistence when credentials are set")


# --------------------------------------------------------------------------
# In-memory repository behavior (alerts, events, cells, drones, media, reports)
# --------------------------------------------------------------------------

def test_in_memory_repository_abstractions():
    repo = InMemoryPersistence()
    mission = _mission_dict("m-mem")
    repo.add_mission(mission)
    assert repo.get_mission("m-mem") == mission
    assert repo.mission_exists("m-mem")

    repo.add_telemetry("m-mem", _telemetry_dict("m-mem"))
    repo.add_telemetry("m-mem", _telemetry_dict("m-mem", drone_id="DRONE-02"))
    assert len(repo.get_telemetry("m-mem")) == 2
    assert {t["drone_id"] for t in repo.get_telemetry("m-mem")} == {"DRONE-01", "DRONE-02"}

    repo.add_detection("m-mem", _detection_dict())
    assert repo.get_detections("m-mem")[0]["class"] == "person"

    cells = repo.save_search_cells("m-mem", [{"latitude": 1.0, "longitude": 2.0}] * 3)
    assert cells == 3
    assert all(c["status"] == "pending" for c in repo.get_search_cells("m-mem"))

    repo.add_mission_event("m-mem", "MISSION_CREATED")
    repo.add_mission_event("m-mem", "DETECTION_RECEIVED")
    assert [e["event_type"] for e in repo.list_mission_events("m-mem")] == [
        "MISSION_CREATED", "DETECTION_RECEIVED",
    ]

    repo.ensure_drone("DRONE-01")
    repo.ensure_drone("DRONE-01")  # idempotent (two telemetry drones already registered)
    assert {d["id"] for d in repo.list_drones()} == {"DRONE-01", "DRONE-02"}

    alert = repo.add_alert("m-mem", severity="high", title="Person found", message="check")
    assert alert["id"] and alert["status"] == "open"
    assert repo.list_alerts("m-mem")[0]["title"] == "Person found"

    media = repo.add_media("m-mem", media_type="image", storage_path="bucket/x.jpg")
    assert repo.list_media("m-mem")[0]["storage_path"] == "bucket/x.jpg"

    report = repo.add_report("m-mem", report_type="mission")
    assert repo.list_reports("m-mem")[0]["id"] == report["id"]
    print("PASS: in-memory repository abstractions (missions/telemetry/detections/cells/events/drones/alerts/media/reports)")


# --------------------------------------------------------------------------
# Supabase repository logic against the fake client
# --------------------------------------------------------------------------

def test_supabase_mission_roundtrip():
    client = _fake_client()
    repo = SupabasePersistence(client)
    mission = _mission_dict("m-sb")
    repo.add_mission(mission)
    assert repo.get_mission("m-sb") == mission
    assert repo.mission_exists("m-sb")
    assert repo.get_mission("missing") is None
    print("PASS: supabase mission roundtrip")


def test_supabase_telemetry_and_drone():
    client = _fake_client()
    repo = SupabasePersistence(client)
    repo.add_mission(_mission_dict("m-t"))
    repo.add_telemetry("m-t", _telemetry_dict("m-t"))
    repo.add_telemetry("m-t", _telemetry_dict("m-t"))  # same drone -> no second upsert
    records = repo.get_telemetry("m-t")
    assert len(records) == 2
    assert set(records[0].keys()) == set(TELEMETRY_FIELDS)
    assert records[0]["source"] == "SIMULATED"
    drones = client.db["drones"]
    assert len(drones) == 1  # drone upserted once
    assert drones[0]["id"] == "DRONE-01"
    print("PASS: supabase telemetry roundtrip with canonical fields and drone upsert")


def test_supabase_detection_roundtrip_no_geo():
    client = _fake_client()
    repo = SupabasePersistence(client)
    repo.add_mission(_mission_dict("m-d"))
    detection = _detection_dict()
    repo.add_detection("m-d", detection)
    records = repo.get_detections("m-d")
    assert len(records) == 1
    assert set(records[0].keys()) == set(DETECTION_FIELDS)
    assert records[0] == detection
    assert "latitude" not in records[0] and "longitude" not in records[0]
    # the stored row carries the association at row level only
    assert client.db["detections"][0]["mission_id"] == "m-d"
    print("PASS: supabase detection roundtrip (canonical fields, mission_id at row level, no geo)")


def test_supabase_search_path_and_cells():
    client = _fake_client()
    repo = SupabasePersistence(client)
    repo.add_mission(_mission_dict("m-p"))
    waypoints = [
        {"latitude": 18.5204, "longitude": 73.8567},
        {"latitude": 18.5204, "longitude": 73.8575},
    ]
    path = {
        "mission_id": "m-p",
        "spacing_m": 85.0,
        "waypoints": waypoints,
        "generated_at": "2026-09-03T16:53:43.235Z",
    }
    repo.set_search_path("m-p", path)
    assert repo.get_search_path("m-p") == path
    count = repo.save_search_cells("m-p", waypoints)
    assert count == 2
    cells = repo.get_search_cells("m-p")
    assert [c["cell_index"] for c in cells] == [0, 1]
    assert all(c["status"] == "pending" for c in cells)
    print("PASS: supabase search path + search cells persistence")


def test_supabase_events_alerts_media_reports():
    client = _fake_client()
    repo = SupabasePersistence(client)
    repo.add_mission(_mission_dict("m-x"))
    repo.add_mission_event("m-x", "MISSION_CREATED", "created")
    repo.add_mission_event("m-x", "SEARCH_PATH_GENERATED", "path")
    events = repo.list_mission_events("m-x")
    assert [e["event_type"] for e in events] == ["MISSION_CREATED", "SEARCH_PATH_GENERATED"]
    assert events[0]["timestamp"].endswith("Z")  # normalized on read-back

    alert = repo.add_alert("m-x", severity="medium", title="possible person", message="", detection_id=None)
    assert alert["id"] and alert["severity"] == "medium"
    assert repo.list_alerts("m-x")[0]["title"] == "possible person"

    media = repo.add_media("m-x", media_type="image", storage_path="media/a.jpg")
    assert repo.list_media("m-x")[0]["storage_path"] == "media/a.jpg"

    report = repo.add_report("m-x", report_type="mission")
    assert report["status"] == "pending"
    assert repo.list_reports("m-x")[0]["report_type"] == "mission"
    print("PASS: supabase events/alerts/media/reports persistence")


def test_supabase_error_wrapping():
    class _Broken:
        def table(self, name):
            class _Boom:
                def insert(self, rows):
                    return self

                def execute(self):
                    raise RuntimeError("connection refused")

            return _Boom()

    repo = SupabasePersistence(_Broken())
    try:
        repo.add_mission(_mission_dict("boom"))
    except PersistenceError as exc:
        assert "connection refused" in str(exc)
    else:
        raise AssertionError("expected PersistenceError")
    print("PASS: supabase failures surface as PersistenceError (no silent success)")


def test_supabase_timestamp_normalization():
    client = _fake_client()
    repo = SupabasePersistence(client)
    repo.add_mission(_mission_dict("m-ts"))
    record = _telemetry_dict("m-ts")
    repo.add_telemetry("m-ts", record)
    # Fake DB would return the string as given; simulate postgREST "+00:00" output.
    client.db["telemetry"][0]["timestamp"] = "2026-09-03T16:53:43.235760+00:00"
    out = repo.get_telemetry("m-ts")[0]
    assert out["timestamp"] == "2026-09-03T16:53:43.235760Z"
    print("PASS: supabase timestamptz normalized to canonical Z form on read-back")


def run_all():
    print("Running database/persistence tests...\n")
    test_config_defaults_disabled()
    test_config_enabled_with_credentials()
    test_placeholder_url_does_not_enable()
    test_fallback_store_is_in_memory()
    test_create_store_selects_supabase_when_configured()
    test_in_memory_repository_abstractions()
    test_supabase_mission_roundtrip()
    test_supabase_telemetry_and_drone()
    test_supabase_detection_roundtrip_no_geo()
    test_supabase_search_path_and_cells()
    test_supabase_events_alerts_media_reports()
    test_supabase_error_wrapping()
    test_supabase_timestamp_normalization()
    print("\nAll database/persistence tests passed.")


if __name__ == "__main__":
    run_all()