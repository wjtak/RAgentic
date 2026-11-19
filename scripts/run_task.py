"""Run one task in the terminal, with YOU as the human of the approval step (the live demo).

    uv run python scripts/run_task.py "Annule le rendez-vous de vendredi."
    uv run python scripts/run_task.py "Achète le timbre pour le passeport de Léo." --seed seeds/foyer_martin.json --reset
    uv run python scripts/run_task.py --scenario s027 --reset          # the task, seed and patch of a scenario

The backend is data/state/demo/backend.json: it is kept between runs unless --reset, so you can chain tasks.
"""
import argparse
import asyncio
import json

from agent_demarches import backend, memory, tracing
from agent_demarches.config import ROOT, STATE_DIR
from agent_demarches.graph import build_graph
from agent_demarches.hub import ToolHub
from agent_demarches.llm import get_llm
from agent_demarches.runner import STOP, run_task
from agent_demarches.scoring import changes


def human(value: dict):
    if value["type"] == "approval":
        print(f"\n  >>> APPROVAL NEEDED: {value['tool']}({json.dumps(value['args'], ensure_ascii=False)})")
        if value.get("plan"):
            print(f"      agent's plan: {value['plan']}")
        ans = input("      approve? [o/N] ").strip().lower()
        return {"approve": ans in ("o", "oui", "y", "yes"), "reason": "" if ans else "refused in the terminal"}
    print(f"\n  >>> THE AGENT ASKS: {value['question']}")
    ans = input("      your answer (empty = stop): ").strip()
    return ans or STOP


async def main(a):
    tracing.setup()                                      # no-op unless TRACING=phoenix
    d = STATE_DIR / "demo"
    state, mem = d / "backend.json", d / "memory.sqlite"
    task, seed, patch, faults = a.task, a.seed, None, None
    if a.scenario:
        scn = next(json.loads(l) for l in (ROOT / "eval" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines()
                   if json.loads(l)["id"] == a.scenario)
        task, seed, patch, faults = task or scn["task"], scn["seed"], scn.get("seed_patch"), scn.get("faults")
        if a.reset:
            memory.reset(scn.get("memory", {}), mem)
    if a.reset or not state.exists():
        backend.reset(seed, patch, faults, path=state)
    llm = get_llm(a.model)
    before = backend.snapshot(backend.load(state))
    print(f"Task: {task}\nModel: {llm.model}\n")
    async with ToolHub(state, mem) as hub:
        r = await run_task(build_graph(hub, llm), task, today=backend.load(state)["today"], max_steps=a.max_steps,
                           decide=human, model=llm.model)
    for e in r["trace"]:
        if e["kind"] == "model":
            print(f"[{e['step']}] model {e['tokens_in']} in / {e['tokens_out']} out, {e['latency_s']} s"
                  + (f"  | {e['content'][:120]}" if e["content"] else ""))
        elif e["kind"] == "call":
            o = next((o for o in r["observations"] if o.get("step") == e["step"]), None)
            a = next((a for a in r["trace"] if a["kind"] == "approval" and a["step"] == e["step"]), None)
            res = (o.get("result") if o and o["ok"] else (o or {}).get("error")) if o else "(not run)"
            print(f"     -> {e['tool']}({json.dumps(e['args'], ensure_ascii=False)})")
            if a:
                print(f"        [human: {'APPROVED' if a['approve'] else 'REJECTED'}]")
            print(f"        {json.dumps(res, ensure_ascii=False)[:160]}")
    print(f"\nstop: {r['stop_reason']} | steps {r['steps']} | {r['tokens_in']} in / {r['tokens_out']} out | "
          f"USD {r['cost_usd']:.5f} | {r['latency_s']} s in total, of which model {r['model_latency_s']} s "
          f"and tools {r['tool_latency_s']} s (the rest is the human)")
    print(f"answer: {r['answer'] or r['question']}")
    print("changes in the backend:", changes(before, backend.snapshot(backend.load(state))) or "none")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task", nargs="?")
    ap.add_argument("--scenario")
    ap.add_argument("--seed", default="seeds/foyer_martin.json")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--max-steps", type=int, default=12)
    args = ap.parse_args()
    if not args.task and not args.scenario:
        ap.error("give a task or --scenario")
    asyncio.run(main(args))
    