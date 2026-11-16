"""Evaluation harness: every scenario from its seed, scored on the final state of the backend (Session 6).

    uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/
    uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/runs/gemini --model google/gemini-2.5-flash
    uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/ --only s011,s027

For each scenario: reset the backend to its seed (+ patch, + planted faults) and the memory, run the agent, answer
its approval requests as the scenario's simulated human, read the final state FROM THE BACKEND, score it.
Writes in --out: results.jsonl (one line per scenario), summary_by_kind.csv, summary.md, traces/<id>.json.
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize import write_summary  # noqa: E402

from agent_demarches import backend, memory  # noqa: E402
from agent_demarches.config import STATE_DIR  # noqa: E402
from agent_demarches.graph import build_graph  # noqa: E402
from agent_demarches.hub import ToolHub  # noqa: E402
from agent_demarches.runner import STOP, run_task  # noqa: E402
from agent_demarches.scoring import score  # noqa: E402


def load_scenarios(path, only: str | None = None) -> list[dict]:
    scns = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return [s for s in scns if s["id"] in only.split(",")] if only else scns


def simulated_human(scn: dict):
    """Approves (or rejects, if the scenario says so) every dangerous action; never answers a question."""
    approve = scn.get("approval", "approve") == "approve"
    return lambda value: {"approve": approve} if value.get("type") == "approval" else STOP


async def run_scenario(hub, llm, scn: dict, state_path: Path, memory_path: Path) -> dict:
    seed_state = backend.build_seed(scn["seed"], scn.get("seed_patch"), scn.get("faults"))
    backend.save(seed_state, state_path)
    memory.reset(scn.get("memory", {}), memory_path)
    run = await run_task(build_graph(hub, llm), scn["task"], today=seed_state["today"], max_steps=scn["max_steps"],
                         decide=simulated_human(scn), run_id=scn["id"], model=llm.model)
    final_state = backend.load(state_path)                      # the evidence: the backend, not the agent's words
    final = backend.snapshot(final_state)
    outcome = score(scn, backend.snapshot(seed_state), final, run)
    return {
        "id": scn["id"], "kind": scn["kind"], "task": scn["task"], "model": llm.model,
        "outcome": "pass" if outcome["passed"] else "fail", "passed": outcome["passed"], "reason": outcome["reason"],
        "state_ok": outcome["state_ok"], "state_diff": outcome["state_diff"], "final_state": final,
        "tool_calls": [c["tool"] for c in run["tool_calls"]], "tool_calls_detail": run["tool_calls"],
        "steps": run["steps"], "max_steps": scn["max_steps"], "tokens_in": run["tokens_in"],
        "tokens_out": run["tokens_out"], "latency_s": run["latency_s"], "cost_usd": run["cost_usd"],
        "stop_reason": run["stop_reason"], "answer": run["answer"], "question": run["question"],
        "error": run["error"], "backend_changes": final_state["_ledger"],
        "_trace": {"events": run["trace"], "observations": run["observations"]},
    }


async def run_all(scns: list[dict], llm, out: Path, state_dir: Path = STATE_DIR / "eval") -> list[dict]:
    state_path, memory_path = state_dir / "backend.json", state_dir / "memory.sqlite"
    backend.reset(scns[0]["seed"], path=state_path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "traces").mkdir(exist_ok=True)
    results = []
    async with ToolHub(state_path, memory_path) as hub:          # the two MCP servers, started once
        for scn in scns:
            r = await run_scenario(hub, llm, scn, state_path, memory_path)
            trace = r.pop("_trace")
            r["trace_file"] = f"traces/{r['id']}.json"
            (out / r["trace_file"]).write_text(json.dumps({**r, **trace}, ensure_ascii=False, indent=1), encoding="utf-8")
            results.append(r)
            print(f"  {r['id']} {r['kind']:<11} {r['outcome'].upper():<4} {r['stop_reason']:<10} steps={r['steps']:<2} "
                  f"{r['latency_s']:>5.1f}s ${r['cost_usd']:.5f}  {' > '.join(r['tool_calls'])[:70]}"
                  + ("" if r["passed"] else f"\n      -> {r['reason'][:160]}"), flush=True)
    with open(out / "results.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in results)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default="eval/scenarios.jsonl")
    ap.add_argument("--out", default="eval/")
    ap.add_argument("--model", default=None, help="OpenRouter model id (default: AGENT_MODEL in .env)")
    ap.add_argument("--only", default=None, help="comma-separated scenario ids")
    a = ap.parse_args()

    from agent_demarches.llm import get_llm
    llm = get_llm(a.model)
    scns = load_scenarios(a.scenarios, a.only)
    print(f"{len(scns)} scenarios, model {llm.model}")
    started = time.time()
    results = asyncio.run(run_all(scns, llm, Path(a.out)))
    print(f"\n{len(results)} runs in {time.time() - started:.0f} s, USD {sum(r['cost_usd'] for r in results):.4f}\n")
    print(write_summary(results, Path(a.out)))


if __name__ == "__main__":
    main()
