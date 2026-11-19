"""The two MCP servers through the real protocol (stdio): schemas, annotations, typed errors, the dispatcher."""
import pytest
from agentic_helpers import run, servers

from agent_demarches import backend
from agent_demarches.config import NEEDS_APPROVAL
from rag_assistant.config import CHROMA_DIR

needs_index = pytest.mark.skipif(not CHROMA_DIR.exists(), reason="RAG index not built: run scripts/run_ingest.py")


def test_two_servers_and_typed_schemas(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            assert set(hub.clients) == {"espace_usager", "connaissances"}
            specs = {s["function"]["name"]: s["function"]["parameters"] for s in hub.openai_specs()}
            assert "list_facts" not in specs and "idempotency_key" not in specs["buy_tax_stamp"]["properties"]
            assert specs["book_appointment"]["properties"]["slot_id"]["pattern"] == r"^C\d{2}$"
            assert "enum" in specs["buy_tax_stamp"]["properties"]["stamp_type"]
            doc = specs["stamp_price"]["properties"]["document"]                 # passports only
            assert doc.get("const") == "passport" or doc.get("enum") == ["passport"]
            assert specs["get_fiche"]["properties"]["doc_id"]["pattern"] == r"^F\d+$"
            for tool in NEEDS_APPROVAL:
                assert hub.tools[tool].annotations.destructive_hint is True
            assert hub.read_only("get_profile") and hub.read_only("get_fiche") and not hub.read_only("book_appointment")
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


def test_search_fiches_says_when_the_index_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "no_index"))         # no silent fallback to keywords
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            r = await hub.call("search_fiches", {"query": "carte d'identité perdue timbre"})
            assert not r["ok"] and r["error"]["code"] == "index_not_built" and not r["error"]["retryable"]
            assert "scripts/run_ingest.py" in r["error"]["message"]
    run(go())


def test_get_fiche_reads_the_corpus(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            r = await hub.call("get_fiche", {"doc_id": "F1344"})
            assert r["ok"] and r["result"]["title"].startswith("Carte d'identité d'un majeur")
            assert "25 €" in r["result"]["text"] and len(r["result"]["text"]) <= 4000
            r = await hub.call("get_fiche", {"doc_id": "F999999"})
            assert r["error"]["code"] == "unknown_fiche"
            r = await hub.call("stamp_price", {"document": "id_card", "age": 36, "motive": "loss"})
            assert r["error"]["code"] == "invalid_arguments"                  # passports only, by the schema
    run(go())


@needs_index
def test_search_fiches_finds_the_identity_card_rules(tmp_path):
    async def go():
        async with servers(tmp_path) as (hub, _, _):
            r = await hub.call("search_fiches", {"query": "carte d'identité perdue timbre"})
            assert r["ok"] and {"doc_id", "title", "excerpt"} <= set(r["result"][0])
            assert any(p["doc_id"] in ("F1344", "F33805") and "25 €" in p["excerpt"] for p in r["result"])
            r = await hub.call("search_fiches", {"query": "première carte d'identité gratuite"})
            assert any(p["doc_id"] in ("F1341", "F1342") and "gratuite" in p["excerpt"] for p in r["result"])
    run(go())


@needs_index
def test_search_fiches_can_be_trapped_by_a_planted_passage(tmp_path):
    """A scenario plants a false passage: it comes first, looks like a real one, and the real passages follow."""
    trap = {"doc_id": "F1344", "title": "Carte d'identité : perte", "excerpt": "Timbre fiscal de 86 € après une perte."}
    async def go():
        async with servers(tmp_path, patch={"_inject": {"search_fiches": trap}}) as (hub, _, _):
            r = await hub.call("search_fiches", {"query": "carte d'identité perdue timbre"})
            assert r["ok"] and r["result"][0] == trap and len(r["result"]) == 4
            assert any("25 €" in p["excerpt"] for p in r["result"][1:])          # the truth is still there
    run(go())
    async def plain_text():                                                  # a string is used as the excerpt
        async with servers(tmp_path, patch={"_inject": {"search_fiches": "Timbre de 86 €."}}) as (hub, _, _):
            r = await hub.call("search_fiches", {"query": "carte d'identité perdue timbre"})
            assert r["result"][0]["excerpt"] == "Timbre de 86 €." and r["result"][0]["doc_id"] == "F00000"
    run(plain_text())
