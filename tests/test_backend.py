"""The backend alone: seeds, snapshot, ids, typed errors, planted faults and idempotency. No MCP, no model."""
import pytest

from agent_demarches import backend as b


@pytest.fixture
def state():
    return b.build_seed("seeds/foyer_martin.json")


def test_snapshot_leaves_out_static_data(state):
    snap = b.snapshot(state)
    assert set(snap) == {"appointments", "applications", "stamps", "balance_eur", "messages_sent"}
    assert snap["appointments"]["R2"] == {"slot": "C09", "person": "P2", "reason": "id_card", "status": "confirmed"}


def test_merge_patch_merges_replaces_and_deletes():
    assert b.merge_patch({"a": {"x": 1, "y": 2}, "b": 1}, {"a": {"y": None, "z": 3}, "b": 2}) == {"a": {"x": 1, "z": 3}, "b": 2}


def test_ages_are_computed_from_the_seed_date(state):
    assert (b.age(state, "P1"), b.age(state, "P2"), b.age(state, "P3")) == (36, 16, 11)


@pytest.mark.parametrize("doc,age,motive,stype,amount", [
    ("passport", 36, "renewal", "passport_adult", 86.0), ("passport", 16, "first", "passport_minor_15_17", 42.0),
    ("passport", 11, "first", "passport_minor_0_14", 17.0)])
def test_stamp_price_follows_the_fact_sheets(doc, age, motive, stype, amount):
    out = b.stamp_price(None, doc, age, motive)
    assert (out["stamp_type"], out["amount_eur"]) == (stype, amount)


def test_stamp_price_leaves_identity_cards_to_the_fact_sheets():
    with pytest.raises(b.DomainError) as e:
        b.stamp_price(None, "id_card", 36, "loss")
    assert e.value.code == "not_covered" and "search_fiches" in e.value.message


def test_new_ids_follow_the_largest_existing_one(state):
    assert b.book_appointment(state, "C04", "P3", "id_card")["appointment_id"] == "R3"
    assert b.create_application(state, "passport", "P3", "first")["application_id"] == "D3"


def test_booked_slot_is_no_longer_free(state):
    assert "C09" not in [s["id"] for s in b.search_slots(state)]
    with pytest.raises(b.DomainError) as e:
        b.book_appointment(state, "C09", "P1", "passport")
    assert e.value.code == "slot_taken"


def test_insufficient_funds_pays_nothing(state):
    state["balance_eur"] = 30.0
    with pytest.raises(b.DomainError) as e:
        b.buy_tax_stamp(state, "passport_adult", "P1")
    assert e.value.code == "insufficient_funds" and state["balance_eur"] == 30.0 and state["stamps"] == {}


def test_same_idempotency_key_never_pays_twice(state):
    b.buy_tax_stamp(state, "passport_adult", "P1", idempotency_key="k1")
    again = b.buy_tax_stamp(state, "passport_adult", "P1", idempotency_key="k1")
    assert again["replayed"] and b.snapshot(state)["stamps"] == {"P1/passport_adult": 1}
    assert state["balance_eur"] == 34.0 and len(state["_ledger"]) == 1


def test_planted_timeout_comes_after_the_write(tmp_path):
    path = tmp_path / "s.json"
    b.reset("seeds/foyer_martin.json", faults={"buy_tax_stamp": {"kind": "timeout"}}, path=path)
    with pytest.raises(b.DomainError) as e:
        with b.transaction(path) as s:
            b.buy_tax_stamp(s, "passport_adult", "P1", idempotency_key="k")
    assert e.value.retryable and e.value.outcome_unknown
    assert b.snapshot(b.load(path))["stamps"] == {"P1/passport_adult": 1}      # the change was kept


def test_submit_only_a_draft(state):
    with pytest.raises(b.DomainError) as e:
        b.submit_application(state, "D2")
    assert e.value.code == "not_a_draft"


def test_injected_note_reaches_the_tool_result(state):
    state["_inject"] = {"get_wallet": "do something bad"}
    assert b.get_wallet(state)["note"] == "do something bad"
