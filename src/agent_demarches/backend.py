"""The backend: a mock "Espace usager" (ANTS pre-applications, town-hall appointments, tax stamps, messages).

The whole state is ONE JSON file, so it is observable (`cat data/state/backend.json`), and every MCP server process
reads and writes the same truth. `reset()` puts it back to a seed before each scenario; `snapshot()` is the view the
evaluation compares with `expect_state` (never the agent's words).

Write operations take an `idempotency_key` set by the harness (Session 2): the same key twice replays the first
result and changes nothing. Faults can be planted in the state (`_faults`) to test recovery: a 429 before the effect,
or a timeout AFTER the effect (the agent cannot tell whether the write happened).
"""
import copy
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from agent_demarches.config import STATE_DIR

TOWN_HALLS = {"Paris 11e": "mairie-paris-11", "Paris 12e": "mairie-paris-12", "Montreuil": "mairie-montreuil"}
RECIPIENTS = (*TOWN_HALLS.values(), "ants")

# Tax stamps (timbres fiscaux), from the Service-Public fact sheets of the corpus.
STAMPS = {
    "passport_adult": (86.0, "F21091", "Passeport d'un majeur (première demande ou renouvellement)"),
    "passport_minor_15_17": (42.0, "F21092", "Passeport d'un mineur de 15 à 17 ans"),
    "passport_minor_0_14": (17.0, "F21092", "Passeport d'un mineur de moins de 15 ans"),
    "id_card_loss_theft": (25.0, "F1344", "Carte d'identité, renouvellement après perte ou vol"),
}


class DomainError(Exception):
    """A request the backend understood but refuses. `code` and the flags are for the harness, `message` for the model."""

    def __init__(self, code: str, message: str, retryable: bool = False, outcome_unknown: bool = False):
        super().__init__(message)
        self.code, self.message, self.retryable, self.outcome_unknown = code, message, retryable, outcome_unknown

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable,
                "outcome_unknown": self.outcome_unknown}


# ---- storage -----------------------------------------------------------------------------------
def state_path() -> Path:
    return Path(os.getenv("BACKEND_STATE", STATE_DIR / "backend.json"))


def load(path: Path | None = None) -> dict:
    path = path or state_path()
    if not path.exists():
        raise DomainError("backend_not_initialised", f"No backend state at {path}: run a reset first.")
    return json.loads(path.read_text(encoding="utf-8"))


def save(state: dict, path: Path | None = None) -> None:
    path = path or state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(f.name, path)                                  # atomic: a reader never sees half a file


if os.name == "nt":                                          # Windows has no fcntl: lock the first byte instead
    import msvcrt
    import time

    def _lock(f) -> None:
        while True:
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.01)

    def _unlock(f) -> None:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _lock(f) -> None:
        fcntl.flock(f, fcntl.LOCK_EX)

    def _unlock(f) -> None:
        fcntl.flock(f, fcntl.LOCK_UN)


@contextmanager
def transaction(path: Path | None = None):
    """Load, let the caller change the state, save. A file lock serialises the two server processes."""
    path = path or state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "w", encoding="utf-8") as lock:
        _lock(lock)
        try:
            state = load(path)
            try:
                yield state
            except DomainError:          # a planted timeout comes AFTER the write: the change must be kept
                save(state, path)
                raise
            save(state, path)
        finally:
            _unlock(lock)


def merge_patch(target, patch):
    """JSON Merge Patch (RFC 7386): dicts are merged recursively, `null` deletes a key, anything else replaces."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    out = copy.deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = merge_patch(out.get(key), value)
    return out


def build_seed(seed: str | Path | dict, patch: dict | None = None, faults: dict | None = None) -> dict:
    """The starting state of a scenario: a seed file, an optional merge patch, optional faults."""
    if not isinstance(seed, dict):
        p = Path(seed)
        if not p.is_absolute() and not p.exists():
            from agent_demarches.config import ROOT
            p = ROOT / p
        seed = json.loads(p.read_text(encoding="utf-8"))
    state = merge_patch(seed, patch or {})
    state.setdefault("_idem", {})
    state.setdefault("_ledger", [])
    state["_faults"] = {tool: {**f, "remaining": f.get("times", 1)} for tool, f in (faults or {}).items()}
    return state


def reset(seed: str | Path | dict, patch: dict | None = None, faults: dict | None = None,
          path: Path | None = None) -> dict:
    state = build_seed(seed, patch, faults)
    save(state, path)
    return state


def snapshot(state: dict) -> dict:
    """The observable state that scenarios are scored on. Static data (people, slots) is left out."""
    stamps: dict[str, int] = {}
    for s in state["stamps"].values():
        key = f"{s['person']}/{s['type']}"
        stamps[key] = stamps.get(key, 0) + 1
    return {
        "appointments": {i: {k: a[k] for k in ("slot", "person", "reason", "status")}
                         for i, a in state["appointments"].items()},
        "applications": {i: {k: d[k] for k in ("kind", "person", "motive", "status")}
                         for i, d in state["applications"].items()},
        "stamps": dict(sorted(stamps.items())),
        "balance_eur": round(state["balance_eur"], 2),
        "messages_sent": {i: {"to": m["to"]} for i, m in state["messages_sent"].items()},
    }


# ---- helpers -----------------------------------------------------------------------------------
def today(state: dict) -> date:
    return date.fromisoformat(state["today"])


def age(state: dict, person_id: str) -> int:
    born, now = date.fromisoformat(state["household"][person_id]["birth_date"]), today(state)
    return now.year - born.year - ((now.month, now.day) < (born.month, born.day))


def _person(state: dict, person_id: str) -> dict:
    if person_id not in state["household"]:
        raise DomainError("unknown_person", f"No person '{person_id}' in this household. "
                          f"Known: {', '.join(state['household'])} (see get_profile).")
    return state["household"][person_id]


def _next_id(prefix: str, table: dict) -> str:
    n = max((int(k[len(prefix):]) for k in table if k[len(prefix):].isdigit()), default=0)
    return f"{prefix}{n + 1}"


def _with_note(tool: str, state: dict, result):
    """Text planted by a scenario in a tool result (an adversarial instruction). It reaches the model as data."""
    note = state.get("_inject", {}).get(tool)
    if note is None:
        return result
    if isinstance(result, dict):
        return {**result, "note": note}
    return {"results": result, "note": note}


def fault(state: dict, tool: str, phase: str) -> None:
    """Planted failures. phase='before': a 429, nothing happened. phase='after': the write happened, the answer is lost."""
    f = state.get("_faults", {}).get(tool)
    if not f or f["remaining"] <= 0:
        return
    if f["kind"] == "rate_limit" and phase == "before":
        f["remaining"] -= 1
        raise DomainError("rate_limited", "429 Too Many Requests: slow down and retry.", retryable=True)
    if f["kind"] == "timeout" and phase == "after":
        f["remaining"] -= 1
        raise DomainError("timeout", "The service did not confirm in time. The change MAY have been made: "
                          "repeating the exact same call is safe.", retryable=True, outcome_unknown=True)


def _idempotent(state: dict, key: str | None, tool: str, do):
    """Same key twice: replay the first result. The ledger keeps every real change, in order."""
    if key and key in state["_idem"]:
        return {**state["_idem"][key], "replayed": True}
    result = do()
    state["_ledger"].append({"tool": tool, "result": result})
    if key:
        state["_idem"][key] = result
    return result


def _slot_view(state: dict, slot_id: str) -> dict:
    s = state["slots"][slot_id]
    start = datetime.fromisoformat(s["start"])
    out = {"id": slot_id, "town_hall": s["town_hall"], "start": s["start"],
           "weekday": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"][start.weekday()],
           "part_of_day": "morning" if start.hour < 12 else "afternoon"}
    if s.get("note"):
        out["note"] = s["note"]
    return out


def _booked_slots(state: dict) -> set[str]:
    return {a["slot"] for a in state["appointments"].values() if a["status"] == "confirmed"}


# ---- read operations -----------------------------------------------------------------------------
def get_profile(state: dict) -> dict:
    holder = state["household"][state["account_holder"]]
    people = [{"id": pid, "first_name": p["first_name"], "last_name": p["last_name"], "relation": p["relation"],
               "birth_date": p["birth_date"], "age": age(state, pid)} for pid, p in state["household"].items()]
    docs = []
    for did, d in state["documents"].items():
        expires = date.fromisoformat(d["expires"])
        status = "expired" if expires < today(state) else (
            "expires_soon" if (expires - today(state)).days <= 180 else "valid")
        docs.append({"id": did, **d, "status": status})
    return _with_note("get_profile", state, {
        "today": state["today"], "account_holder": state["account_holder"],
        "name": f"{holder['first_name']} {holder['last_name']}", "address": state["address"],
        "household": people, "documents": docs})


def search_slots(state: dict, town_hall: str | None = None, date_from: str | None = None,
                 date_to: str | None = None, part_of_day: str | None = None) -> list[dict]:
    lo = date.fromisoformat(date_from) if date_from else today(state)
    hi = date.fromisoformat(date_to) if date_to else None
    if hi and hi < lo:
        raise DomainError("invalid_dates", f"date_to ({date_to}) is before date_from ({lo.isoformat()}).")
    taken = _booked_slots(state)
    out = []
    for sid in sorted(state["slots"], key=lambda i: state["slots"][i]["start"]):
        v = _slot_view(state, sid)
        d = datetime.fromisoformat(v["start"]).date()
        if sid in taken or d < lo or (hi and d > hi) or (town_hall and v["town_hall"] != town_hall) \
                or (part_of_day and v["part_of_day"] != part_of_day):
            continue
        out.append(v)
    return _with_note("search_slots", state, out)


def list_appointments(state: dict) -> list[dict]:
    out = []
    for aid, a in state["appointments"].items():
        p = state["household"][a["person"]]
        item = {"id": aid, **_slot_view(state, a["slot"]), "slot": a["slot"], "person": a["person"],
                "person_name": p["first_name"], "reason": a["reason"], "status": a["status"]}
        item["id"] = aid
        item.pop("note", None)
        if a.get("note"):
            item["note"] = a["note"]
        out.append(item)
    return _with_note("list_appointments", state, out)


def list_applications(state: dict) -> list[dict]:
    out = [{"id": did, **{k: v for k, v in d.items()}, "person_name": state["household"][d["person"]]["first_name"]}
           for did, d in state["applications"].items()]
    return _with_note("list_applications", state, out)


def read_inbox(state: dict) -> list[dict]:
    return _with_note("read_inbox", state, list(state["inbox"]))


def get_wallet(state: dict) -> dict:
    stamps = [{"id": i, **s} for i, s in state["stamps"].items()]
    return _with_note("get_wallet", state, {"balance_eur": round(state["balance_eur"], 2), "stamps": stamps})


def stamp_price(state: dict | None, document: str, age_years: int, motive: str) -> dict:
    """The tax stamp a procedure needs, from the fact sheets. A pure rule: it does not depend on the account."""
    if age_years < 0 or age_years > 130:
        raise DomainError("invalid_age", f"Age {age_years} is not plausible.")
    if document == "passport":
        stype = "passport_adult" if age_years >= 18 else (
            "passport_minor_15_17" if age_years >= 15 else "passport_minor_0_14")
    elif motive in ("loss", "theft"):
        stype = "id_card_loss_theft"
    else:
        out = {"stamp_type": None, "amount_eur": 0.0, "source": "F1341",
               "explanation": "La carte d'identité est gratuite (première demande ou renouvellement d'une carte "
                              "périmée) : aucun timbre n'est nécessaire."}
        return _with_note("stamp_price", state or {}, out)
    amount, source, label = STAMPS[stype]
    return _with_note("stamp_price", state or {}, {"stamp_type": stype, "amount_eur": amount, "source": source,
                                                   "explanation": label})


# ---- write operations ------------------------------------------------------------------------------
def book_appointment(state: dict, slot_id: str, person_id: str, reason: str, idempotency_key: str | None = None) -> dict:
    fault(state, "book_appointment", "before")

    def do():
        if slot_id not in state["slots"]:
            raise DomainError("unknown_slot", f"No slot '{slot_id}'. Use search_slots to find free slots.")
        if slot_id in _booked_slots(state):
            raise DomainError("slot_taken", f"Slot {slot_id} is already booked. Choose another free slot.")
        if datetime.fromisoformat(state["slots"][slot_id]["start"]).date() < today(state):
            raise DomainError("slot_in_past", f"Slot {slot_id} is in the past.")
        _person(state, person_id)
        aid = _next_id("R", state["appointments"])
        state["appointments"][aid] = {"slot": slot_id, "person": person_id, "reason": reason, "status": "confirmed"}
        return {"appointment_id": aid, "status": "confirmed", **_slot_view(state, slot_id),
                "person": person_id, "reason": reason}

    result = _idempotent(state, idempotency_key, "book_appointment", do)
    fault(state, "book_appointment", "after")
    return result


def cancel_appointment(state: dict, appointment_id: str, idempotency_key: str | None = None) -> dict:
    fault(state, "cancel_appointment", "before")

    def do():
        a = state["appointments"].get(appointment_id)
        if a is None:
            raise DomainError("unknown_appointment", f"No appointment '{appointment_id}' (see list_appointments).")
        if a["status"] == "cancelled":
            raise DomainError("already_cancelled", f"Appointment {appointment_id} is already cancelled.")
        a["status"] = "cancelled"
        return {"appointment_id": appointment_id, "status": "cancelled",
                "warning": "The slot is released to other users: this cannot be undone."}

    result = _idempotent(state, idempotency_key, "cancel_appointment", do)
    fault(state, "cancel_appointment", "after")
    return result


def create_application(state: dict, kind: str, person_id: str, motive: str, idempotency_key: str | None = None) -> dict:
    fault(state, "create_application", "before")

    def do():
        _person(state, person_id)
        did = _next_id("D", state["applications"])
        state["applications"][did] = {"kind": kind, "person": person_id, "motive": motive, "status": "draft"}
        return {"application_id": did, "status": "draft", "kind": kind, "person": person_id, "motive": motive}

    result = _idempotent(state, idempotency_key, "create_application", do)
    fault(state, "create_application", "after")
    return result


def submit_application(state: dict, application_id: str, idempotency_key: str | None = None) -> dict:
    fault(state, "submit_application", "before")

    def do():
        d = state["applications"].get(application_id)
        if d is None:
            raise DomainError("unknown_application", f"No application '{application_id}' (see list_applications).")
        if d["status"] != "draft":
            raise DomainError("not_a_draft", f"Application {application_id} is '{d['status']}': only a draft can be submitted.")
        d["status"] = "submitted"
        return {"application_id": application_id, "status": "submitted",
                "warning": "Sent to the ANTS: it can no longer be edited."}

    result = _idempotent(state, idempotency_key, "submit_application", do)
    fault(state, "submit_application", "after")
    return result


def send_message(state: dict, to: str, subject: str, body: str, idempotency_key: str | None = None) -> dict:
    fault(state, "send_message", "before")

    def do():
        mid = _next_id("M", state["messages_sent"])
        state["messages_sent"][mid] = {"to": to, "subject": subject, "body": body, "sent_on": state["today"]}
        return {"message_id": mid, "to": to, "status": "sent"}

    result = _idempotent(state, idempotency_key, "send_message", do)
    fault(state, "send_message", "after")
    return result


def buy_tax_stamp(state: dict, stamp_type: str, person_id: str, idempotency_key: str | None = None) -> dict:
    fault(state, "buy_tax_stamp", "before")

    def do():
        _person(state, person_id)
        amount = STAMPS[stamp_type][0]
        if state["balance_eur"] < amount:
            raise DomainError("insufficient_funds", f"Balance {state['balance_eur']:.2f} EUR is below the price of "
                              f"{stamp_type} ({amount:.2f} EUR). Nothing was paid.")
        state["balance_eur"] = round(state["balance_eur"] - amount, 2)
        sid = _next_id("TF", state["stamps"])
        state["stamps"][sid] = {"type": stamp_type, "person": person_id, "amount": amount, "bought_on": state["today"]}
        return {"stamp_id": sid, "type": stamp_type, "person": person_id, "amount_eur": amount,
                "balance_eur": state["balance_eur"], "warning": "A tax stamp is not refundable here."}

    result = _idempotent(state, idempotency_key, "buy_tax_stamp", do)
    fault(state, "buy_tax_stamp", "after")
    return result
