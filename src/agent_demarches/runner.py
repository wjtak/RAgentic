"""Run one task to its end: invoke the graph, answer its interrupts with a policy, collect the trace.

Used by the evaluation (the policy is the scenario's simulated human), the CLI and the UI (the policy is a person).
"""
import time
import uuid

STOP = object()          # a policy returns STOP to end the run on an interrupt (e.g. the agent asked a question)


async def run_task(app, task: str, *, today: str, max_steps: int = 10, run_id: str | None = None,
                   decide=None, model: str = "") -> dict:
    """`decide(interrupt_value) -> resume value | STOP`. Default: approve every action, stop on every question."""
    from langgraph.types import Command
    decide = decide or default_policy
    run_id = run_id or uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 4 * max_steps + 20}
    started = time.perf_counter()
    interrupts, question, error = [], None, None
    try:
        out = await app.ainvoke({"task": task, "today": today, "run_id": run_id, "max_steps": max_steps}, config)
        while out.get("__interrupt__"):                  # the graph paused: approval or question
            value = out["__interrupt__"][0].value
            interrupts.append(value)
            resume = decide(value)
            if resume is STOP:
                if value.get("type") == "question":
                    question = value.get("question")
                break
            out = await app.ainvoke(Command(resume=resume), config)
    except Exception as e:                               # an API outage must be visible, never look like a pass
        error = f"{type(e).__name__}: {e}"[:300]
    state = (await app.aget_state(config)).values
    result = collect(state, interrupts, question, error)
    result.update(run_id=run_id, model=model, latency_s=round(time.perf_counter() - started, 3))
    return result


def default_policy(value: dict):
    return {"approve": True} if value.get("type") == "approval" else STOP


def collect(state: dict, interrupts: list, question: str | None, error: str | None) -> dict:
    """The fields the evaluation needs, from the final checkpoint of the run."""
    events, observations = state.get("events", []), state.get("observations", [])
    by_step = {o["step"]: o for o in observations if "step" in o}
    approvals = {e["step"]: e for e in events if e["kind"] == "approval"}
    calls = []
    for e in events:
        if e["kind"] != "call":
            continue
        o, ap = by_step.get(e["step"]), approvals.get(e["step"])
        calls.append({"step": e["step"], "tool": e["tool"], "args": e["args"],
                      "executed": bool(o and o.get("executed")), "ok": bool(o and o.get("ok")),
                      "error": (o or {}).get("error", {}).get("code") if o and not o.get("ok") else None,
                      "attempts": (o or {}).get("attempts"), "approved": ap["approve"] if ap else None,
                      "latency_s": (o or {}).get("latency_s")})
    models = [e for e in events if e["kind"] == "model"]
    if error:
        stop = "error"
    elif question is not None:
        stop = "asked_user"
    elif interrupts and state.get("stop_reason") is None:
        stop = "interrupted"
    else:
        stop = state.get("stop_reason") or "error"
    return {
        "answer": state.get("answer"), "question": question, "stop_reason": stop, "error": error,
        "steps": state.get("steps", 0), "tool_calls": calls,
        "tokens_in": sum(m["tokens_in"] for m in models), "tokens_out": sum(m["tokens_out"] for m in models),
        "cost_usd": round(sum(m["cost_usd"] for m in models), 6),
        "model_latency_s": round(sum(m["latency_s"] for m in models), 3),
        "tool_latency_s": round(sum(o.get("latency_s") or 0 for o in observations), 3),
        "interrupts": interrupts, "trace": events, "observations": observations,
    }
