-- The durable event log: one row per harness event.
-- DBOS keeps its own tables for recovery; this one is ours, for the UI and humans.

CREATE TABLE IF NOT EXISTS event_log (
  id         bigserial   PRIMARY KEY,
  run_id     text        NOT NULL,
  seq        integer     NOT NULL,              -- order within a run; deterministic, so recovery can't duplicate
  type       text        NOT NULL,              -- run.started, tool.requested, ...
  data       jsonb       NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, seq)                          -- writing the same event twice becomes a no-op
);

CREATE INDEX IF NOT EXISTS event_log_type_idx ON event_log (type);
