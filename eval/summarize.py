"""Results per kind (Session 6), and the comparison of several runs (two models on the same scenarios).

    uv run python eval/summarize.py eval/runs/gemini                        # one run: summary.md in that folder
    uv run python eval/summarize.py eval/runs/v1 --out tmp/                 # one run, written elsewhere (v1 untouched)
    uv run python eval/summarize.py eval/runs/v1 eval/runs/gemini           # comparison -> eval/comparison.md

One folder: summary.md and summary_by_kind.csv go to --out if given, else into that folder (a results.jsonl file:
into its folder). Several folders: comparison.md and comparison.csv go to --out, else to eval/.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

KINDS = ["normal", "ambiguous", "impossible", "adversarial"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% interval of a pass rate. With ~6 scenarios per kind it is wide: say so in the defence."""
    if n == 0:
        return 0.0, 0.0
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def load(path: str | Path) -> list[dict]:
    p = Path(path)
    p = p / "results.jsonl" if p.is_dir() else p
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _median(sel: list[dict], key: str):
    """Median of a field that older results (eval/runs/v1) do not have: "-" when absent."""
    values = [r[key] for r in sel if r.get(key) is not None]
    return round(statistics.median(values), 2) if values else "-"


def per_kind(results: list[dict]) -> list[dict]:
    rows = []
    for kind in [*KINDS, "ALL"]:
        sel = [r for r in results if kind in ("ALL", r["kind"])]
        if not sel:
            continue
        k = sum(r["passed"] for r in sel)
        lo, hi = wilson(k, len(sel))
        fails = Counter(r["reason"].split(":", 1)[0] for r in sel if not r["passed"])
        rows.append({
            "kind": kind, "runs": len(sel), "passed": k, "pass_rate": round(k / len(sel), 3),
            "ci95": f"{lo:.0%}-{hi:.0%}", "state_ok": round(sum(r["state_ok"] for r in sel) / len(sel), 3),
            "mean_steps": round(statistics.mean(r["steps"] for r in sel), 2),
            "mean_tokens_in": round(statistics.mean(r["tokens_in"] for r in sel)),
            "mean_tokens_out": round(statistics.mean(r["tokens_out"] for r in sel)),
            "cost_usd_total": round(sum(r["cost_usd"] for r in sel), 5),
            "cost_usd_per_run": round(sum(r["cost_usd"] for r in sel) / len(sel), 6),
            "latency_s_median": round(statistics.median(r["latency_s"] for r in sel), 2),
            "latency_s_max": round(max(r["latency_s"] for r in sel), 2),
            "model_latency_s_median": _median(sel, "model_latency_s"),
            "tool_latency_s_median": _median(sel, "tool_latency_s"),
            "failures": ", ".join(f"{n}x {c}" for c, n in fails.most_common()) or "-",
        })
    return rows


def markdown(rows: list[dict], cols: list[str]) -> str:
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    out += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(out)


def write_summary(results: list[dict], out_dir: Path) -> str:
    rows = per_kind(results)
    with open(out_dir / "summary_by_kind.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    model = results[0].get("model", "?")
    cols = ["kind", "runs", "passed", "pass_rate", "ci95", "state_ok", "mean_steps", "mean_tokens_in",
            "mean_tokens_out", "cost_usd_per_run", "latency_s_median", "model_latency_s_median",
            "tool_latency_s_median", "failures"]
    failed = [r for r in results if not r["passed"]]
    text = [f"# Results: {model}", "", markdown(rows, cols), "", f"## Failed runs ({len(failed)})", ""]
    text += [f"- **{r['id']}** ({r['kind']}) {r['task']} -> `{r['reason']}`; calls: "
             f"{' > '.join(r['tool_calls']) or '-'}; stop: {r['stop_reason']}" for r in failed]
    (out_dir / "summary.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return markdown(rows, cols)


def compare(dirs: list[str], out: Path) -> str:
    """One row per (run, kind): pass rate, cost and latency, for the model comparison bonus."""
    rows = []
    for d in dirs:
        results = load(d)
        model = results[0].get("model", Path(d).name)
        for r in per_kind(results):
            rows.append({"model": model, **{k: r[k] for k in ("kind", "runs", "pass_rate", "ci95", "mean_steps",
                                                              "cost_usd_per_run", "latency_s_median",
                                                              "model_latency_s_median", "tool_latency_s_median")}})
    cols = ["model", "kind", "runs", "pass_rate", "ci95", "mean_steps", "cost_usd_per_run", "latency_s_median",
            "model_latency_s_median", "tool_latency_s_median"]
    table = markdown(rows, cols)
    out.mkdir(parents=True, exist_ok=True)
    (out / "comparison.md").write_text("# Model comparison, same scenarios\n\n" + table + "\n", encoding="utf-8")
    with open(out / "comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return table


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", default=None, help="output folder (default: the run's folder, or eval/ to compare)")
    a = ap.parse_args()
    if len(a.dirs) == 1:
        src = Path(a.dirs[0])
        out = Path(a.out) if a.out else (src if src.is_dir() else src.parent)
        out.mkdir(parents=True, exist_ok=True)
        print(write_summary(load(src), out))
    else:
        print(compare(a.dirs, Path(a.out or "eval")))
    sys.exit(0)
