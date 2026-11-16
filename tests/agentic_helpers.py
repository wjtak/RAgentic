"""Shared helpers for the tests of the agentic part: a fresh backend + memory + the 4 MCP servers, no model."""
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from agent_demarches import backend, memory  # noqa: E402
from agent_demarches.hub import ToolHub  # noqa: E402


@asynccontextmanager
async def servers(tmp_path: Path, seed="seeds/foyer_martin.json", **kw):
    state, mem = tmp_path / "backend.json", tmp_path / "memory.sqlite"
    backend.reset(seed, path=state, **kw)
    memory.reset({}, mem)
    async with ToolHub(state, mem) as hub:
        hub.retry_delay = 0.01
        yield hub, state, mem


def run(coro):
    return asyncio.run(coro)
