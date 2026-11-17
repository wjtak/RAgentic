"""What the two MCP servers share: annotations, typed arguments and the typed error (Sessions 1-2)."""
import json
from typing import Annotated, Literal

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from agent_demarches import backend

# What each kind of tool does, for the client. Writes are idempotent only because the harness sends a key.
READ = ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False, openWorldHint=False)
DANGEROUS = ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=True, openWorldHint=False)

# Constrained argument types: the JSON schema the model reads is built from these.
PersonId = Annotated[str, Field(pattern=r"^P\d+$", description="Person id from get_profile, e.g. P1")]
SlotId = Annotated[str, Field(pattern=r"^C\d{2}$", description="Slot id from search_slots, e.g. C04")]
AppointmentId = Annotated[str, Field(pattern=r"^R\d+$", description="Appointment id, e.g. R1")]
ApplicationId = Annotated[str, Field(pattern=r"^D\d+$", description="Pre-application id, e.g. D1")]
IsoDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="A date, YYYY-MM-DD")]
TownHall = Literal["Paris 11e", "Paris 12e", "Montreuil"]
Recipient = Literal["mairie-paris-11", "mairie-paris-12", "mairie-montreuil", "ants"]
Reason = Literal["passport", "id_card"]
PartOfDay = Literal["morning", "afternoon"]
Motive = Literal["first", "renewal", "loss", "theft"]
StampType = Literal["passport_adult", "passport_minor_15_17", "passport_minor_0_14", "id_card_loss_theft"]
IdemKey = Annotated[str | None, Field(description="Set by the harness, never by the model")]


def tool_error(e: backend.DomainError) -> ToolError:
    """A typed error: `message` is for the model; `code`, `retryable`, `outcome_unknown` for the harness."""
    return ToolError(json.dumps(e.as_dict(), ensure_ascii=False))


def read(fn, *args, **kwargs):
    """A read on the current state (planted 429s are counted, so the state is written back)."""
    try:
        with backend.transaction() as state:
            backend.fault(state, getattr(fn, "__name__", ""), "before")
            return fn(state, *args, **kwargs)
    except backend.DomainError as e:
        raise tool_error(e) from None


def write(fn, *args, **kwargs):
    """A write inside one locked transaction."""
    try:
        with backend.transaction() as state:
            return fn(state, *args, **kwargs)
    except backend.DomainError as e:
        raise tool_error(e) from None
