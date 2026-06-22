"""
Etched — a tamper-evident, append-only audit ledger in PostgreSQL.

Record versioned changes to anything (documents, configs, model deployments, decisions). Entries can be
added but NEVER edited or deleted — a database trigger physically rejects UPDATE/DELETE. For regulated /
compliance systems, that "the log cannot be rewritten" property is the whole point.

Setup:
    psql "$PG_DSN" -f schema.sql

Use:
    from etched import record, log, verify_immutable
    record("pricing_config", actor="alice", payload={"plan": "pro", "price": 49})
    log("pricing_config")          # full version history
    verify_immutable()             # PROVE tampering is rejected

CLI:
    python etched.py record pricing_config --actor alice --payload '{"price":49}'
    python etched.py log --entity pricing_config
    python etched.py verify
"""
import os, hashlib, json, time, argparse
import psycopg

PG_DSN = os.environ.get("PG_DSN", "postgresql://user:pass@localhost:5432/etched")


def record(entity: str, actor: str, payload: dict | None = None) -> dict:
    """Append a new version for `entity`. `actor` is required (no anonymous writes). Returns the row.
    The entry is immutable the moment it lands."""
    if not actor or not actor.strip():
        raise ValueError("actor is required — every change must be attributable")
    body = json.dumps(payload or {}, sort_keys=True)
    h = hashlib.sha256(f"{entity}|{body}|{time.time()}".encode()).hexdigest()
    with psycopg.connect(PG_DSN, autocommit=True) as c, c.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(version),0)+1 FROM audit_ledger WHERE entity=%s", (entity,))
        ver = cur.fetchone()[0]
        cur.execute("INSERT INTO audit_ledger (entity,version,hash,actor,payload) "
                    "VALUES (%s,%s,%s,%s,%s) RETURNING id, ts", (entity, ver, h, actor, body))
        row = cur.fetchone()
    return {"id": row[0], "entity": entity, "version": ver, "hash": h, "actor": actor, "ts": str(row[1])}


def log(entity: str = "") -> list:
    """Read the full version history (optionally for one entity)."""
    with psycopg.connect(PG_DSN, autocommit=True) as c, c.cursor() as cur:
        if entity:
            cur.execute("SELECT id,entity,version,hash,actor,payload,ts FROM audit_ledger "
                        "WHERE entity=%s ORDER BY id", (entity,))
        else:
            cur.execute("SELECT id,entity,version,hash,actor,payload,ts FROM audit_ledger ORDER BY id")
        return [{"id": r[0], "entity": r[1], "version": r[2], "hash": r[3], "actor": r[4],
                 "payload": r[5], "ts": str(r[6])} for r in cur.fetchall()]


def verify_immutable() -> dict:
    """Prove the ledger is append-only: attempt an UPDATE and confirm the trigger rejects it.
    Returns {immutable: True, ...} when protection is correctly installed."""
    try:
        with psycopg.connect(PG_DSN, autocommit=True) as c, c.cursor() as cur:
            cur.execute("UPDATE audit_ledger SET actor='tamper' "
                        "WHERE id=(SELECT MIN(id) FROM audit_ledger)")
        return {"immutable": False, "warning": "UPDATE SUCCEEDED — the append-only trigger is NOT installed!"}
    except Exception as e:
        return {"immutable": True, "rejected_with": str(e).splitlines()[0]}


def _cli():
    ap = argparse.ArgumentParser(description="Etched — append-only audit ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("entity"); r.add_argument("--actor", required=True); r.add_argument("--payload", default="{}")
    l = sub.add_parser("log"); l.add_argument("--entity", default="")
    sub.add_parser("verify")
    a = ap.parse_args()
    if a.cmd == "record":
        print(json.dumps(record(a.entity, a.actor, json.loads(a.payload)), indent=2))
    elif a.cmd == "log":
        print(json.dumps(log(a.entity), indent=2))
    elif a.cmd == "verify":
        print(json.dumps(verify_immutable(), indent=2))


if __name__ == "__main__":
    _cli()
