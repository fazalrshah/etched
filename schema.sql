-- Etched — a tamper-evident, append-only audit ledger in PostgreSQL.
-- The table can be INSERTed into, but UPDATE/DELETE are physically rejected by a trigger,
-- so the history cannot be rewritten — exactly what compliance/audit needs.

CREATE TABLE IF NOT EXISTS audit_ledger (
    id       BIGSERIAL PRIMARY KEY,
    entity   TEXT        NOT NULL,            -- what is versioned (doc id, config key, model name, ...)
    version  BIGINT      NOT NULL,            -- monotonic per entity
    hash     TEXT        NOT NULL,            -- content hash for integrity
    actor    TEXT        NOT NULL,            -- who/what made the change (required — no anonymous writes)
    payload  JSONB,                           -- optional structured detail
    ts       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity, version)
);

-- The guarantee: reject any attempt to alter or remove history.
CREATE OR REPLACE FUNCTION forbid_ledger_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_ledger is append-only: % on % is forbidden', TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_ledger_append_only ON audit_ledger;
CREATE TRIGGER audit_ledger_append_only
    BEFORE UPDATE OR DELETE ON audit_ledger
    FOR EACH ROW EXECUTE FUNCTION forbid_ledger_mutation();
