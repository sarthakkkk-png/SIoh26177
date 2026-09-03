-- AetherSAR - Supabase/PostgreSQL schema (Phase 6)
--
-- Paste the whole file into the Supabase SQL editor and run it.
--
-- Security assumption (MVP): the backend talks to Supabase with the
-- service-role key (backend-side only) and the API is the only data
-- consumer, so Row Level Security is intentionally not enabled yet.
-- Revisit RLS before any frontend accesses the database directly.
--
-- IDs are `text` so application-generated ids (uuid4().hex) are stored
-- exactly as produced. Canonical telemetry/detection field names from
-- simulator/telemetry.py and cv/detection.py are used as column names;
-- no second schema is introduced.

create table if not exists public.missions (
  id text primary key,
  name text not null default '',
  status text not null default 'created',
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  search_area jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.drones (
  id text primary key,
  name text not null,
  status text not null default 'IDLE',
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.telemetry (
  id bigint generated always as identity primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  drone_id text not null references public.drones(id),
  "timestamp" timestamptz not null,
  latitude double precision not null check (latitude >= -90 and latitude <= 90),
  longitude double precision not null check (longitude >= -180 and longitude <= 180),
  altitude_m double precision not null,
  heading_deg double precision not null,
  speed_mps double precision not null,
  battery_pct double precision not null check (battery_pct >= 0 and battery_pct <= 100),
  status text not null,
  current_waypoint integer not null check (current_waypoint >= 0),
  total_waypoints integer not null check (total_waypoints >= 0),
  source text not null default 'SIMULATED' check (source = 'SIMULATED')
);

create index if not exists telemetry_mission_time_idx
  on public.telemetry (mission_id, "timestamp");

create table if not exists public.search_paths (
  mission_id text primary key references public.missions(id) on delete cascade,
  spacing_m double precision not null check (spacing_m > 0),
  waypoints jsonb not null,
  generated_at timestamptz not null default now()
);

create table if not exists public.search_cells (
  id bigint generated always as identity primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  cell_index integer not null check (cell_index >= 0),
  latitude double precision not null check (latitude >= -90 and latitude <= 90),
  longitude double precision not null check (longitude >= -180 and longitude <= 180),
  status text not null default 'pending',
  searched_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  unique (mission_id, cell_index)
);

create index if not exists search_cells_mission_idx
  on public.search_cells (mission_id);

create table if not exists public.detections (
  id bigint generated always as identity primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  drone_id text not null,
  frame_id integer not null check (frame_id >= 0),
  "class" text not null,
  confidence double precision not null check (confidence >= 0 and confidence <= 1),
  bbox jsonb not null,
  "timestamp" timestamptz not null
);

create index if not exists detections_mission_time_idx
  on public.detections (mission_id, "timestamp");

create table if not exists public.alerts (
  id text primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  detection_id bigint references public.detections(id) on delete set null,
  severity text not null check (severity in ('low', 'medium', 'high')),
  title text not null,
  message text not null default '',
  status text not null default 'open',
  created_at timestamptz not null default now(),
  acknowledged_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists alerts_mission_idx on public.alerts (mission_id);

create table if not exists public.mission_events (
  id bigint generated always as identity primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  event_type text not null,
  message text not null default '',
  "timestamp" timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists mission_events_mission_time_idx
  on public.mission_events (mission_id, "timestamp");

create table if not exists public.media (
  id text primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  detection_id bigint references public.detections(id) on delete set null,
  media_type text not null,
  storage_path text not null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists media_mission_idx on public.media (mission_id);

create table if not exists public.reports (
  id text primary key,
  mission_id text not null references public.missions(id) on delete cascade,
  report_type text not null default 'mission',
  status text not null default 'pending',
  storage_path text,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists reports_mission_idx on public.reports (mission_id);
