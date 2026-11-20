"""The held-out set (eval/scenarios_holdout.jsonl): well-formed, distinct from the training set, achievable, scored right."""
import json

import pytest
from agentic_helpers import ROOT, run, servers
from oracle_holdout import HOLDOUT_RAG, NAIVE_HOLDOUT, ORACLE_HOLDOUT
from oracle_plans import policy_for

import run_eval
from agent_demarches.llm import ScriptedLLM
from rag_assistant.config import CHROMA_DIR

HOLDOUT = run_eval.load_scenarios(ROOT / "eval" / "scenarios_holdout.jsonl")
TRAIN = run_eval.load_scenarios(ROOT / "eval" / "scenarios.jsonl")


def test_holdout_is_well_formed_and_covers_every_kind():
    kinds = [s["kind"] for s in HOLDOUT]
    assert len(HOLDOUT) == 40 and len({s["id"] for s in HOLDOUT}) == len(HOLDOUT)
    assert all(s["id"].startswith("h") for s in HOLDOUT)
    for kind in ("normal", "ambiguous", "impossible", "adversarial"):
        assert kind in kinds, kind
    for s in HOLDOUT:
        assert {"id", "kind", "task", "seed", "expect_state", "forbid_calls", "max_steps"} <= set(s)
        assert "remember" in s["forbid_calls"]
        if s["kind"] in ("ambiguous", "impossible"):
            assert s["expect_state"] == {}, s["id"]
    assert set(ORACLE_HOLDOUT) == {s["id"] for s in HOLDOUT}


def test_holdout_does_not_copy_the_training_set():
    train_tasks = {s["task"].strip().lower() for s in TRAIN}
    for s in HOLDOUT:
        assert s["task"].strip().lower() not in train_tasks, f"{s['id']} copies a training task"
    # no held-out scenario reaches the same final change from the same seed as a training one (traps ignored)
    def key(s):
        return json.dumps([s["seed"], s["expect_state"]], sort_keys=True, ensure_ascii=False)
    train_keys = {key(s) for s in TRAIN if s["expect_state"]}
    assert not [s["id"] for s in HOLDOUT if s["expect_state"] and key(s) in train_keys]


def _run(tmp_path, plans):
    async def go():
        out = []
        async with servers(tmp_path) as (hub, state, mem):
            for s in HOLDOUT:
                if s["id"] in plans:
                    out.append(await run_eval.run_scenario(hub, ScriptedLLM(policy_for(plans[s["id"]])), s, state, mem))
        return out
    return run(go())


def test_reference_plans_pass_the_holdout(tmp_path):
    results = _run(tmp_path, {k: v for k, v in ORACLE_HOLDOUT.items() if k not in HOLDOUT_RAG})
    assert len(results) == len(HOLDOUT) - len(HOLDOUT_RAG)
    assert all(r["passed"] for r in results), [(r["id"], r["reason"]) for r in results if not r["passed"]]


@pytest.mark.skipif(not CHROMA_DIR.exists(), reason="RAG index not built: run scripts/run_ingest.py")
def test_reference_plans_pass_the_holdout_rag_scenarios(tmp_path):
    results = _run(tmp_path, {k: ORACLE_HOLDOUT[k] for k in HOLDOUT_RAG})
    assert all(r["passed"] for r in results), [(r["id"], r["reason"]) for r in results if not r["passed"]]


def test_naive_agent_fails_the_holdout(tmp_path):
    results = {r["id"]: r for r in _run(tmp_path, NAIVE_HOLDOUT)}
    assert "forbidden_call" in results["h006"]["reason"] and "wrong_stop" in results["h006"]["reason"]
    assert "forbidden_call: submit_application" in results["h008"]["reason"]
    assert "appointments.R1.status" in results["h010"]["reason"]
    assert "stamps.P1/passport_adult" in results["h011"]["reason"]
    assert results["h003"]["passed"]           # trying to pay without the money is refused by the backend: harmless
    assert "appointments.R2.status" in results["h024"]["reason"]
    assert "forbidden_call: buy_tax_stamp" in results["h034"]["reason"]
    assert "forbidden_call: submit_application" in results["h038"]["reason"]
    assert "appointments.R1.status" in results["h040"]["reason"]
