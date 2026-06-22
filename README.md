# 🪨 Etched — a tamper-evident, append-only audit ledger (PostgreSQL)

For regulated, compliance, or high-trust systems you often need to prove **what changed, when, and by
whom — and that the log itself was never altered.** Most apps log to ordinary tables you *could* quietly
`UPDATE` or `DELETE`, so the audit trail isn't actually trustworthy.

Etched makes the history **physically immutable**: you can `INSERT` new versions, but `UPDATE` and
`DELETE` are **rejected by a database trigger**. The past can't be rewritten — not by the app, not by a
buggy migration, not by an agent, not even by a careless admin query.

> **The guarantee, proven:** Etched ships a `verify_immutable()` that *attempts* to tamper and confirms
> the database refuses. Trust, but verify — automatically.

## Why this beats "just log it"

| Ordinary audit log | Etched |
|---|---|
| Rows can be edited/deleted | `UPDATE`/`DELETE` raise an exception (trigger) |
| Anonymous writes | `actor` required on every entry |
| "Probably wasn't tampered with" | A test that *proves* tampering is rejected |
| App-enforced (bypassable via SQL) | **Database-enforced** (can't be bypassed by the app) |

## Quickstart

```bash
pip install -r requirements.txt
export PG_DSN="postgresql://user:pass@localhost:5432/etched"
psql "$PG_DSN" -f schema.sql          # creates the table + the append-only trigger
```

```python
from etched import record, log, verify_immutable

record("pricing_config", actor="alice", payload={"plan": "pro", "price": 49})
record("pricing_config", actor="bob",   payload={"plan": "pro", "price": 59})

log("pricing_config")        # -> v1 (alice), v2 (bob), with hashes + timestamps
verify_immutable()           # -> {"immutable": True, "rejected_with": "audit_ledger is append-only: UPDATE ... is forbidden"}
```

CLI:
```bash
python etched.py record pricing_config --actor alice --payload '{"price":49}'
python etched.py log --entity pricing_config
python etched.py verify
```

## How it works

The whole guarantee is a `BEFORE UPDATE OR DELETE` trigger that `RAISE`s an exception (see
[`schema.sql`](schema.sql)). Because it's enforced **in the database**, not the application, there's no
code path — ORM, raw SQL, or otherwise — that can rewrite history. Each row carries a content `hash` and
a required `actor` for integrity and attribution.

## Hard-won lesson

App-level "immutability" is a suggestion; a malformed query or a future code change can blow right past
it. Push the guarantee **down to the database trigger** and it becomes structural. Then add a
`verify_immutable()` to your test suite so a missing trigger fails CI loudly — protection you don't test
is protection you don't have.

## Built by

Built by **[KodeKing](https://www.kodeking.net)** · author **[Fazal Shah](https://www.fazalshah.com)**.
We build local, private, multi-agent AI systems for teams who can't send their data to the cloud.
Issues and PRs welcome.

## License

MIT — see [LICENSE](LICENSE).
