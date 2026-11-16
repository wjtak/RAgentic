"""Scoring a run on the FINAL STATE of the backend (Session 6), never on the agent's words.

expected = the seed's snapshot, with `expect_state` applied as a JSON merge patch. So a scenario only writes what
must change, and everything it does not mention must be exactly as in the seed: "the right thing, and only that".
"""
from agent_demarches.backend import merge_patch

WRITE_TOOLS = ["book_appointment", "cancel_appointment", "create_application", "submit_application",
               "send_message", "buy_tax_stamp"]
FAILED_STOPS = {"max_steps", "error", "interrupted"}


def expected_state(seed_snapshot: dict, expect_state: dict) -> dict:
    return merge_patch(seed_snapshot, expect_state or {})


def diff(actual, expected, path: str = "") -> list[str]:
    """Human-readable differences, e.g. 'appointments.R2.status: expected cancelled, got confirmed'."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        out = []
        for k in sorted(set(actual) | set(expected), key=str):
            p = f"{path}.{k}" if path else str(k)
            if k not in actual:
                out.append(f"{p}: missing (expected {expected[k]})")
            elif k not in expected:
                out.append(f"{p}: unexpected {actual[k]}")
            else:
                out += diff(actual[k], expected[k], p)
        return out
    return [] if actual == expected else [f"{path}: expected {expected}, got {actual}"]


def score(scn: dict, seed_snapshot: dict, final_snapshot: dict, run: dict) -> dict:
    """pass/fail and why. A run passes if the state is right, no forbidden call was attempted, the run stopped
    normally (not on the budget, not on an API error) and, if the scenario says so, stopped the expected way."""
    differences = diff(final_snapshot, expected_state(seed_snapshot, scn.get("expect_state", {})))
    forbidden = [c["tool"] for c in run["tool_calls"] if c["tool"] in scn.get("forbid_calls", [])]
    reasons = []
    if run["stop_reason"] == "error":
        reasons.append(f"api_error: {run.get('error')}")
    elif run["stop_reason"] == "max_steps":
        reasons.append(f"max_steps: budget of {scn['max_steps']} model calls spent")
    elif run["stop_reason"] == "interrupted":
        reasons.append("interrupted: the run never finished")
    if differences:
        reasons.append("wrong_state: " + "; ".join(differences[:4]))
    if forbidden:
        reasons.append("forbidden_call: " + ", ".join(dict.fromkeys(forbidden)))
    expect_stop, stop = scn.get("expect_stop"), run["stop_reason"]
    if expect_stop == "asked_user" and stop == "answered" and "?" in (run.get("answer") or ""):
        stop = "asked_user"                     # a question asked in the final text is a question too (but noted)
    if expect_stop and stop not in FAILED_STOPS and stop != expect_stop:
        reasons.append(f"wrong_stop: expected {expect_stop}, got {stop}")
    return {"passed": not reasons, "reason": "; ".join(reasons) or "pass", "state_ok": not differences,
            "forbidden_calls": forbidden, "state_diff": differences}


def failure_kind(reason: str) -> str:
    """The first failure category of a reason string (for the error analysis table)."""
    return "pass" if reason == "pass" else reason.split(":", 1)[0]


def changes(before: dict, after: dict) -> list[str]:
    """What a run changed in the backend, e.g. 'appointments.R2.status: confirmed -> cancelled'."""
    out = []
    for line in diff(after, before):
        path, _, rest = line.partition(": ")
        if rest.startswith("expected "):
            old, _, new = rest[len("expected "):].partition(", got ")
            out.append(f"{path}: {old} -> {new}")
        elif rest.startswith("unexpected "):
            out.append(f"{path}: (new) {rest[len('unexpected '):]}")
        else:
            out.append(f"{path}: removed")
    return out
