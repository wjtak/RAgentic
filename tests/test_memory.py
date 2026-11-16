"""Session 4 requirement: one long-term memory, and a test showing it changes a later run.

Run 1 (one conversation): the user states a preference; the agent stores it with `remember` (connaissances MCP server).
Run 2 (a NEW conversation, new thread, backend reset): "book my passport appointment next week, as usual".
- with the memory of run 1, the `recall` node puts the facts in the prompt, and the agent books C04 (Paris 12e, morning);
- with an empty memory, the same request is ambiguous: the agent asks, and nothing changes.

The model is scripted so the test is deterministic and free: it decides ONLY from what the prompt contains, which
is what the memory changes. `eval/memory_check.py` runs the same experiment with the real model.
"""
from agentic_helpers import run, servers

from agent_demarches import backend, memory
from agent_demarches.graph import build_graph
from agent_demarches.llm import ScriptedLLM
from agent_demarches.runner import run_task

TELL = "Retiens que je préfère toujours la mairie du 12e, et les rendez-vous le matin."
ASK = "Prends-moi un rendez-vous pour renouveler mon passeport la semaine prochaine, comme d'habitude."


def model():
    """Remembers when told to; books from KNOWN FACTS when they settle the request; otherwise asks."""
    def policy(messages):
        system, task = messages[0]["content"], messages[1]["content"]
        done = sum(m["role"] == "tool" for m in messages)
        if task.startswith("Retiens"):
            plan = [("remember", {"key": "mairie_preferee", "value": "Paris 12e"}),
                    ("remember", {"key": "horaire_prefere", "value": "le matin"})]
            return ("C'est noté.", []) if done >= len(plan) else ("", [plan[done]])
        if done:
            return "Fait.", []
        facts = system.split("KNOWN FACTS about the user")[-1]
        if "Paris 12e" in facts and "matin" in facts:
            return "", [("book_appointment", {"slot_id": "C04", "person_id": "P1", "reason": "passport"})]
        return "", [("ask_user", {"question": "Dans quelle mairie, et à quel moment de la journée ?"})]
    return ScriptedLLM(policy)


def test_memory_written_in_one_run_changes_a_later_run(tmp_path):
    async def go():
        async with servers(tmp_path, seed="seeds/sans_rdv.json") as (hub, state, mem):
            # run 1: tell
            r1 = await run_task(build_graph(hub, model()), TELL, today="2026-11-16", max_steps=4)
            assert memory.facts("U1", mem) == {"horaire_prefere": "le matin", "mairie_preferee": "Paris 12e"}

            # run 2, with the memory
            backend.reset("seeds/sans_rdv.json", path=state)
            with_mem = await run_task(build_graph(hub, model()), ASK, today="2026-11-16", max_steps=6)
            booked = backend.snapshot(backend.load(state))["appointments"]

            # run 2, same request, memory erased
            backend.reset("seeds/sans_rdv.json", path=state)
            memory.reset({}, mem)
            without = await run_task(build_graph(hub, model()), ASK, today="2026-11-16", max_steps=6)
            unchanged = backend.snapshot(backend.load(state))["appointments"]
        return r1, with_mem, booked, without, unchanged

    _, with_mem, booked, without, unchanged = run(go())
    assert "Paris 12e" in with_mem["trace"][0]["facts"]                       # recall read it
    assert booked == {"R1": {"slot": "C04", "person": "P1", "reason": "passport", "status": "confirmed"}}
    assert without["stop_reason"] == "asked_user" and unchanged == {}
