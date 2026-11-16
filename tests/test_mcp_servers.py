"""The two MCP servers through the real protocol (stdio): schemas, annotations, typed errors, the dispatcher."""
from agentic_helpers import run, servers

from agent_demarches import backend
from agent_demarches.config import NEEDS_APPROVAL


def test_two_servers_and_typed_schemas(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            assert set(hub.clients) == {"espace_usager", "connaissances"}
            specs = {s["function"]["name"]: s["function"]["parameters"] for s in hub.openai_specs()}
            assert "list_facts" not in specs and "idempotency_key" not in specs["buy_tax_stamp"]["properties"]
            assert specs["book_appointment"]["properties"]["slot_id"]["pattern"] == r"^C\d{2}$"
            assert "enum" in specs["buy_tax_stamp"]["properties"]["stamp_type"]
            for tool in NEEDS_APPROVAL:
                assert hub.tools[tool].annotations.destructive_hint is True
            assert hub.read_only("get_profile") and not hub.read_only("book_appointment")
    run(go())


def test_typed_errors_reach_the_model_as_data(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            r = await hub.call("book_appointment", {"slot_id": "C99", "person_id": "P1", "reason": "passport"})
            assert not r["ok"] and r["error"]["code"] == "unknown_slot" and r["attempts"] == 1
            r = await hub.call("search_slots", {"town_hall": "Lyon 3e"})
            assert r["error"]["code"] == "invalid_arguments"
    run(go())


def test_dispatcher_retries_429_and_replays_a_timed_out_payment(tmp_path):
    faults = {"search_slots": {"kind": "rate_limit", "times": 2}, "buy_tax_stamp": {"kind": "timeout"}}
    async def go():
        async with servers(tmp_path, faults=faults) as (hub, state, _):
            r = await hub.call("search_slots", {"town_hall": "Montreuil"})
            assert r["ok"] and r["attempts"] == 3
            r = await hub.call("buy_tax_stamp", {"stamp_type": "passport_adult", "person_id": "P1"}, "run1")
            assert r["ok"] and r["attempts"] == 2 and r["result"]["replayed"]
            assert backend.snapshot(backend.load(state))["stamps"] == {"P1/passport_adult": 1}
    run(go())


def test_memory_server_refuses_secrets(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            assert (await hub.call("remember", {"key": "mairie préférée", "value": "Paris 12e"}))["ok"]
            r = await hub.call("remember", {"key": "code", "value": "mon mot de passe est 1234"})
            assert r["error"]["code"] == "refused"
            assert (await hub.call("list_facts", {}))["result"] == {"mairie_preferee": "Paris 12e"}
    run(go())
