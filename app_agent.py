"""Flask web UI for the Service-Public agent.

Run: uv run python app_agent.py
URL: http://localhost:5070
"""
import asyncio
import json
import os
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from flask import Flask, jsonify, request, send_from_directory
from langgraph.types import Command

from agent_demarches import backend, memory, tracing
from agent_demarches.config import STATE_DIR
from agent_demarches.graph import build_graph
from agent_demarches.hub import ToolHub
from agent_demarches.llm import get_llm
from agent_demarches.runner import collect
from agent_demarches.scoring import changes

app = Flask(__name__, static_folder="static_agent")

UI_DIR = STATE_DIR / "ui"
STATE_PATH = UI_DIR / "backend.json"
MEM_PATH = UI_DIR / "memory.sqlite"
DEFAULT_SEED = "seeds/foyer_martin.json"
DEMO_IDS = ("s004", "s015", "s034")

# Persistent asyncio loop to keep MCP servers (ToolHub) and graph state alive
_loop = asyncio.new_event_loop()
_lock = threading.Lock()
_runtime = {
    "ready": False,
    "error": None,
    "hub": None,
    "llm": None,
    "graph": None,
    "runs": {},  # run_id -> {"config": ..., "started": ..., "before": ..., "interrupts": ...}
}


def _run_coro(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


async def _init_async():
    tracing.setup()
    UI_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        backend.reset(DEFAULT_SEED, None, None, path=STATE_PATH)
    if not MEM_PATH.exists():
        memory.reset({}, MEM_PATH)

    llm = get_llm()
    hub = ToolHub(STATE_PATH, MEM_PATH)
    await hub.__aenter__()
    graph = build_graph(hub, llm)

    _runtime["llm"] = llm
    _runtime["hub"] = hub
    _runtime["graph"] = graph
    _runtime["ready"] = True
    print(f"Agent UI ready at http://localhost:5070 (model: {llm.model})", flush=True)


def _start_loop():
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(_init_async())
    except Exception as err:  # noqa: BLE001
        _runtime["error"] = str(err)
        traceback.print_exc()
    _loop.run_forever()


def _load_demo_scenarios() -> list[dict]:
    path = ROOT / "eval" / "scenarios.jsonl"
    if not path.exists():
        return []
    demos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scn = json.loads(line)
        if scn.get("id") in DEMO_IDS:
            demos.append({
                "id": scn["id"],
                "kind": scn.get("kind", ""),
                "task": scn["task"],
                "seed": scn.get("seed", DEFAULT_SEED),
                "seed_patch": scn.get("seed_patch"),
                "faults": scn.get("faults"),
                "memory": scn.get("memory", {}),
            })
    return sorted(demos, key=lambda x: DEMO_IDS.index(x["id"]))


def _format_response(run_id: str, out: dict | None, error: str | None = None, stopped_question: str | None = None):
    meta = _runtime["runs"][run_id]
    graph = _runtime["graph"]
    state_vals = _run_coro(graph.aget_state(meta["config"])).values
    interrupt_val = None
    if out and out.get("__interrupt__"):
        interrupt_val = out["__interrupt__"][0].value
        meta["interrupts"].append(interrupt_val)

    collected = collect(state_vals, meta["interrupts"], stopped_question, error)
    collected["run_id"] = run_id
    collected["model"] = _runtime["llm"].model
    collected["latency_s"] = round(time.perf_counter() - meta["started"], 2)

    current_backend = backend.load(STATE_PATH)
    diff = changes(meta["before"], backend.snapshot(current_backend))

    return {
        "status": "interrupted" if interrupt_val else "done",
        "interrupt": interrupt_val,
        "result": collected,
        "backend": current_backend,
        "changes": diff,
    }


@app.route("/")
def index():
    return send_from_directory("static_agent", "index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "ready": _runtime["ready"],
        "error": _runtime["error"],
        "model": _runtime["llm"].model if _runtime["llm"] else None,
        "demos": _load_demo_scenarios(),
        "seeds": sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "seeds").glob("*.json")),
    })


@app.route("/api/state")
def api_state():
    if not STATE_PATH.exists():
        return jsonify({"error": "Backend not initialized"}), 503
    return jsonify({"backend": backend.load(STATE_PATH)})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    if not _runtime["ready"]:
        return jsonify({"error": "Agent is still loading..."}), 503
    data = request.get_json(silent=True) or {}
    seed = data.get("seed") or DEFAULT_SEED
    patch = data.get("seed_patch")
    faults = data.get("faults")
    mem_seed = data.get("memory") or {}

    with _lock:
        backend.reset(seed, patch, faults, path=STATE_PATH)
        memory.reset(mem_seed, MEM_PATH)
        _runtime["runs"].clear()
        current = backend.load(STATE_PATH)
    return jsonify({"ok": True, "backend": current})


@app.route("/api/run", methods=["POST"])
def api_run():
    if not _runtime["ready"]:
        return jsonify({"error": "Agent is still loading..."}), 503
    data = request.get_json(silent=True) or {}
    task = (data.get("task") or "").strip()
    max_steps = int(data.get("max_steps") or 12)
    if not task:
        return jsonify({"error": "Empty task."}), 400

    with _lock:
        run_id = uuid.uuid4().hex[:8]
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 4 * max_steps + 20}
        current = backend.load(STATE_PATH)
        _runtime["runs"][run_id] = {
            "config": config,
            "started": time.perf_counter(),
            "before": backend.snapshot(current),
            "interrupts": [],
        }
        payload = {"task": task, "today": current["today"], "run_id": run_id, "max_steps": max_steps}
        try:
            out = _run_coro(_runtime["graph"].ainvoke(payload, config))
            return jsonify(_format_response(run_id, out))
        except Exception as err:  # noqa: BLE001
            traceback.print_exc()
            return jsonify(_format_response(run_id, None, error=f"{type(err).__name__}: {err}")), 500


@app.route("/api/resume", methods=["POST"])
def api_resume():
    if not _runtime["ready"]:
        return jsonify({"error": "Agent is still loading..."}), 503
    data = request.get_json(silent=True) or {}
    run_id = data.get("run_id")
    if not run_id or run_id not in _runtime["runs"]:
        return jsonify({"error": "Run not found or expired."}), 404

    meta = _runtime["runs"][run_id]
    with _lock:
        if data.get("stop"):
            last_q = meta["interrupts"][-1].get("question") if meta["interrupts"] else None
            return jsonify(_format_response(run_id, None, stopped_question=last_q))

        resume_value = data.get("resume")
        try:
            out = _run_coro(_runtime["graph"].ainvoke(Command(resume=resume_value), meta["config"]))
            return jsonify(_format_response(run_id, out))
        except Exception as err:  # noqa: BLE001
            traceback.print_exc()
            return jsonify(_format_response(run_id, None, error=f"{type(err).__name__}: {err}")), 500


if __name__ == "__main__":
    threading.Thread(target=_start_loop, daemon=True).start()
    app.run(host="127.0.0.1", port=5070, debug=False, threaded=True)