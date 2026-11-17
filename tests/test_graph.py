"""The LangGraph graph with a scripted model: the guard, the step budget, the question to the user."""
from agentic_helpers import run, servers

from agent_demarches import backend
from agent_demarches.graph import as_decision, build_graph
from agent_demarches.llm import ScriptedLLM
from agent_demarches.runner import STOP, run_task

CANCEL = ("cancel_appointment", {"appointment_id": "R2"})


def scripted(*steps):
    it = iter(steps)
    return ScriptedLLM(lambda messages: next(it, ("Terminé.", [])))


def test_dangerous_call_waits_for_a_human_and_a_rejection_changes_nothing(tmp_path):
    seen = []

    def human(value):
        seen.append(value)
        return {"approve": False, "reason": "non"}

    async def go():
        async with servers(tmp_path) as (hub, state, _):
            app = build_graph(hub, scripted(("Plan: annuler R2.", [CANCEL]), ("D'accord, rien n'est annulé.", [])))
            r = await run_task(app, "Annule le rendez-vous de vendredi.", today="2026-11-16", decide=human)
            assert seen[0] == {"type": "approval", "tool": "cancel_appointment", "args": {"appointment_id": "R2"},
                               "plan": "Plan: annuler R2."}
            assert r["tool_calls"][0]["approved"] is False and not r["tool_calls"][0]["executed"]
            assert backend.snapshot(backend.load(state))["appointments"]["R2"]["status"] == "confirmed"
            assert r["stop_reason"] == "answered"
    run(go())


def test_approved_call_runs(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, state, _):
            app = build_graph(hub, scripted(("", [CANCEL]), ("Annulé.", [])))
            r = await run_task(app, "Annule le rendez-vous de vendredi.", today="2026-11-16")
            assert r["tool_calls"][0]["approved"] and r["tool_calls"][0]["executed"]
            assert backend.snapshot(backend.load(state))["appointments"]["R2"]["status"] == "cancelled"
    run(go())


def test_read_tools_skip_the_guard(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            app = build_graph(hub, scripted(("", [("get_profile", {})]), ("ok", [])))
            r = await run_task(app, "Qui suis-je ?", today="2026-11-16", decide=lambda v: 1 / 0)   # never called
            assert r["stop_reason"] == "answered" and r["interrupts"] == []
    run(go())


def test_step_budget_stops_a_looping_agent(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            loop = ScriptedLLM(lambda messages: ("", [("get_profile", {})]))
            r = await run_task(build_graph(hub, loop), "Boucle.", today="2026-11-16", max_steps=4)
            assert r["stop_reason"] == "max_steps" and r["steps"] == 4 and loop.calls == 4
            assert sum(c["executed"] for c in r["tool_calls"]) == 3          # the 4th call is never run
    run(go())


def test_ask_user_stops_the_run_or_resumes_with_the_answer(tmp_path):
    ask = ("ask_user", {"question": "Quel rendez-vous ?"})

    async def go():
        async with servers(tmp_path) as (hub, _, _):
            r = await run_task(build_graph(hub, scripted(("", [ask]))), "Annule le rendez-vous.", today="2026-11-16")
            assert r["stop_reason"] == "asked_user" and r["question"] == "Quel rendez-vous ?"
            answered = scripted(("", [ask]), ("", [CANCEL]), ("Annulé.", []))
            r = await run_task(build_graph(hub, answered), "Annule le rendez-vous.", today="2026-11-16",
                               decide=lambda v: "Celui de Léo" if v["type"] == "question" else {"approve": True})
            assert r["stop_reason"] == "answered" and [c["tool"] for c in r["tool_calls"]] == ["ask_user", CANCEL[0]]
    run(go())


def test_invalid_json_arguments_are_reported_not_run(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            app = build_graph(hub, scripted(("", [("cancel_appointment", None)]), ("ok", [])))
            r = await run_task(app, "x", today="2026-11-16")
            assert r["tool_calls"][0]["error"] == "invalid_json" and not r["tool_calls"][0]["executed"]
    run(go())


def test_as_decision_accepts_text_and_json():
    assert as_decision("oui")["approve"] and not as_decision("no")["approve"]
    assert as_decision('{"approve": true}')["approve"] and as_decision(True)["approve"]
    assert STOP is not None
