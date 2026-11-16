"""Read one evaluated run from its trace (for the defence: one success, one failure).

    uv run python scripts/show_trace.py s011                 # from eval/traces/
    uv run python scripts/show_trace.py s027 --dir eval/runs/gemini
"""
import argparse
import json
from pathlib import Path


def show(path: Path) -> None:
    t = json.loads(path.read_text())
    print(f"{t['id']} ({t['kind']}) {t['task']}\nmodel {t['model']} | outcome {t['outcome'].upper()} | {t['reason']}")
    print(f"stop {t['stop_reason']} | steps {t['steps']}/{t['max_steps']} | {t['tokens_in']} in / {t['tokens_out']} out"
          f" | USD {t['cost_usd']:.5f} | {t['latency_s']} s\n")
    obs = {o["step"]: o for o in t["observations"] if "step" in o}
    approvals = {e["step"]: e for e in t["events"] if e["kind"] == "approval"}
    for e in t["events"]:
        if e["kind"] == "recall":
            print(f"recall  memory: {e['facts']}")
        elif e["kind"] == "model":
            print(f"[{e['step']}] LLM  {e['tokens_in']} in / {e['tokens_out']} out  {e['latency_s']} s  ${e['cost_usd']:.6f}"
                  + (f"\n      says: {e['content'][:200]}" if e["content"] else ""))
        elif e["kind"] == "call":
            o = obs.get(e["step"])
            print(f"      CALL {e['tool']}({json.dumps(e['args'], ensure_ascii=False)})")
            if e["step"] in approvals:
                a = approvals[e["step"]]
                print(f"      HUMAN {'approved' if a['approve'] else 'REJECTED: ' + a.get('reason', '')}")
            if o:
                body = o.get("result") if o["ok"] else {"error": o["error"]}
                retry = f"  (attempts {o['attempts']}: {o.get('retried_errors')})" if o.get("attempts", 1) > 1 else ""
                print(f"      -> {json.dumps(body, ensure_ascii=False)[:300]}{retry}")
            else:
                print("      -> (not run)")
        elif e["kind"] == "stop":
            print(f"STOP {e['reason']} after {e['step']} model calls")
    print(f"\nanswer: {t['answer'] or t['question'] or '-'}")
    print(f"final state differs from expected: {t['state_diff'] or 'no'}")
    print(f"real changes in the backend (ledger): {[c['tool'] for c in t['backend_changes']] or 'none'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--dir", default="eval")
    a = ap.parse_args()
    show(Path(a.dir) / "traces" / f"{a.id}.json")
