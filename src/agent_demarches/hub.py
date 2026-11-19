"""The MCP client side: start the two servers, list their tools for the model, and call them through a dispatcher.

The dispatcher is the harness of Session 2, between the agent and the servers:
- the model never sees `idempotency_key`: the harness sets it, the same for the same (run, tool, arguments);
- a typed error marked `retryable` (429, timeout) is retried with the SAME key, so a write that timed out after
  being done is replayed by the backend, not done twice;
- any other error goes back to the model, as data it can read.
"""
import asyncio
import hashlib
import json
import os
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import Client, StdioServerParameters

from agent_demarches.config import HIDDEN_TOOLS, MAX_ATTEMPTS, RETRY_BASE_DELAY, ROOT, SERVERS_DIR

SERVERS = {name: SERVERS_DIR / f"{name}_server.py" for name in ("espace_usager", "connaissances")}


def idem_key(run_id: str, tool: str, args: dict) -> str:
    """Same run, same tool, same arguments = same key (Session 3, `idem_key`)."""
    return hashlib.sha256(json.dumps([run_id, tool, args], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def parse_error(text: str) -> dict:
    """The typed error raised by a server ({code, message, retryable...}), or a validation error from the schema."""
    try:
        return json.loads(text[text.index("{"):])
    except ValueError:
        message = text.replace("Error executing tool ", "").split("For further information")[0].strip()
        return {"code": "invalid_arguments" if "validation error" in text else "tool_error",
                "message": message[:400], "retryable": False, "outcome_unknown": False}


READ_TIMEOUT_S = 300   # the first search_fiches waits for the models to load: > 120 s on a slow or busy machine


class ToolHub:
    """`async with ToolHub(state_dir) as hub:` starts the servers on stdio; `await hub.call(tool, args, run_id)`."""

    def __init__(self, backend_state: Path, memory_db: Path, user_id: str = "U1"):
        self.env = {**os.environ, "BACKEND_STATE": str(backend_state), "MEMORY_DB": str(memory_db),
                    "AGENT_USER": user_id, "PYTHONPATH": os.pathsep.join(
                        [str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep)}
        self.clients: dict[str, Client] = {}
        self.owner: dict[str, str] = {}          # tool name -> server name
        self.tools: dict[str, object] = {}       # tool name -> mcp Tool
        self.retry_delay = RETRY_BASE_DELAY

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        for name, path in SERVERS.items():
            params = StdioServerParameters(command=sys.executable, args=[str(path)], env=self.env, cwd=str(ROOT))
            client = await self._stack.enter_async_context(Client(params, read_timeout_seconds=READ_TIMEOUT_S))
            self.clients[name] = client
            for tool in (await client.list_tools()).tools:
                self.owner[tool.name], self.tools[tool.name] = name, tool
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    # ---- what the model sees ---------------------------------------------------------------------------
    def keyed(self, tool: str) -> bool:
        return "idempotency_key" in self.tools[tool].input_schema.get("properties", {})

    def read_only(self, tool: str) -> bool:
        a = self.tools[tool].annotations
        return bool(a and a.read_only_hint)

    def openai_specs(self) -> list[dict]:
        """The tools in the OpenAI function-calling format, without the harness-only argument."""
        specs = []
        for name, tool in self.tools.items():
            if name in HIDDEN_TOOLS:
                continue
            schema = json.loads(json.dumps(tool.input_schema))
            schema.get("properties", {}).pop("idempotency_key", None)
            schema.pop("title", None)
            for prop in schema.get("properties", {}).values():
                prop.pop("title", None)
            specs.append({"type": "function", "function": {
                "name": name, "description": f"[{self.owner[name]}] {tool.description}", "parameters": schema}})
        return specs

    # ---- the dispatcher ----------------------------------------------------------------------------------
    async def call(self, tool: str, args: dict, run_id: str = "run") -> dict:
        """One logical call, with retries. Returns {ok, result | error, attempts, latency_s, idempotency_key}."""
        started = time.perf_counter()
        if tool not in self.tools:
            return {"ok": False, "error": {"code": "unknown_tool", "message": f"No tool named '{tool}'.",
                                           "retryable": False}, "attempts": 0, "latency_s": 0.0}
        call_args, key = dict(args), None
        if self.keyed(tool):
            key = idem_key(run_id, tool, args)
            call_args["idempotency_key"] = key
        errors = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                res = await self.clients[self.owner[tool]].call_tool(tool, call_args)
            except Exception as e:                                   # transport failure: report it, do not crash
                err = {"code": "transport", "message": f"{type(e).__name__}: {e}"[:300], "retryable": False}
            else:
                if not res.is_error:
                    return {"ok": True, "result": _content(res), "attempts": attempt, "errors": errors,
                            "latency_s": round(time.perf_counter() - started, 3), "idempotency_key": key}
                err = parse_error(res.content[0].text if res.content else "")
            errors.append(err)
            if not err.get("retryable") or attempt == MAX_ATTEMPTS:
                break
            await asyncio.sleep(self.retry_delay * 2 ** (attempt - 1))
        return {"ok": False, "error": err, "attempts": attempt, "errors": errors,
                "latency_s": round(time.perf_counter() - started, 3), "idempotency_key": key}


def _content(res):
    if res.structured_content is not None:
        sc = res.structured_content
        return sc["result"] if set(sc) == {"result"} else sc
    text = "".join(getattr(c, "text", "") for c in res.content)
    try:
        return json.loads(text)
    except ValueError:
        return text
