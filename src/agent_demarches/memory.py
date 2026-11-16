"""Long-term memory (Session 4, layer 4 "profile"): exact facts about a user, found by key, kept across runs.

One SQLite file ($MEMORY_DB). The graph reads every fact of the user at the start of a run (`recall` node) and puts
them in the system prompt as KNOWN FACTS; the model writes with the `remember` tool of the "connaissances" MCP server.
An update keeps the previous values in `history` (the upsert of Session 4); secrets are never stored (write guard).
"""
import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

from agent_demarches.config import STATE_DIR

SENSITIVE = re.compile(r"password|mot de passe|iban|carte bancaire|card number|secret|api[_ -]?key|token|"
                       r"num[ée]ro de passeport|\b\d{2}[A-Z]{2}\d{5}\b", re.I)


def db_path() -> Path:
    return Path(os.getenv("MEMORY_DB", STATE_DIR / "memory.sqlite"))


def _connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS facts (user_id TEXT, key TEXT, value TEXT, history TEXT, "
                "PRIMARY KEY (user_id, key))")
    return con


def upsert(user_id: str, key: str, value: str, path: Path | None = None) -> dict:
    key = "".join(c for c in unicodedata.normalize("NFKD", key.strip().lower()) if not unicodedata.combining(c))
    key = re.sub(r"[^a-z0-9_]+", "_", key).strip("_")[:40]
    if not key or not value.strip():
        raise ValueError("key and value must be non-empty")
    if SENSITIVE.search(key) or SENSITIVE.search(value):
        raise PermissionError("sensitive content (password, card, document number...) is never stored")
    with _connect(path) as con:
        row = con.execute("SELECT value, history FROM facts WHERE user_id=? AND key=?", (user_id, key)).fetchone()
        history = json.loads(row[1]) if row else []
        if row and row[0] != value:
            history.append(row[0])
        con.execute("INSERT OR REPLACE INTO facts VALUES (?, ?, ?, ?)", (user_id, key, value[:200], json.dumps(history)))
    return {"key": key, "value": value[:200], "previous": history[-1] if history else None}


def facts(user_id: str, path: Path | None = None) -> dict[str, str]:
    with _connect(path) as con:
        return dict(con.execute("SELECT key, value FROM facts WHERE user_id=? ORDER BY key", (user_id,)).fetchall())


def forget(user_id: str, key: str, path: Path | None = None) -> bool:
    with _connect(path) as con:
        return con.execute("DELETE FROM facts WHERE user_id=? AND key=?", (user_id, key)).rowcount > 0


def reset(seed_facts: dict[str, dict[str, str]] | None = None, path: Path | None = None) -> None:
    """Empty the memory, then load `{user_id: {key: value}}` (a scenario's starting memory)."""
    with _connect(path) as con:
        con.execute("DELETE FROM facts")
    for user_id, items in (seed_facts or {}).items():
        for key, value in items.items():
            upsert(user_id, key, value, path)


def as_prompt(items: dict[str, str]) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in items.items()) or "(none)"
