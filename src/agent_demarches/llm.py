"""The model: OpenAI-compatible chat completions with native tool calling, through OpenRouter (as in Sessions 2-7).

Every call returns its tokens, its cost and its latency, so the trace of a run can be priced. `ScriptedLLM` replays
a decision function instead of calling a model: the tests use it to check the graph, the guard and the harness
without a key and without cost.
"""
import json
import os
import time
from dataclasses import dataclass, field

from agent_demarches.config import DEFAULT_MODEL, MAX_TOKENS, OPENROUTER_BASE_URL, PRICES


@dataclass
class Reply:
    content: str
    tool_calls: list[dict] = field(default_factory=list)     # [{"id", "name", "arguments": dict | None, "raw": str}]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    model: str = ""


def price(model: str, tokens_in: int, tokens_out: int) -> float:
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    return (tokens_in * p_in + tokens_out * p_out) / 1e6


class OpenRouterLLM:
    def __init__(self, model: str | None = None):
        from dotenv import find_dotenv, load_dotenv
        from openai import AsyncOpenAI
        load_dotenv(find_dotenv(usecwd=True))
        if not os.getenv("OPENROUTER_API_KEY"):
            raise SystemExit("No OPENROUTER_API_KEY: put it in .env at the repository root (see .env.example).")
        self.model = model or os.getenv("AGENT_MODEL", DEFAULT_MODEL)
        self.client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=os.environ["OPENROUTER_API_KEY"],
                                  max_retries=3, timeout=90)

    async def chat(self, messages: list[dict], tools: list[dict]) -> Reply:
        started = time.perf_counter()
        r = await self.client.chat.completions.create(model=self.model, messages=messages, tools=tools,
                                                      temperature=0, max_tokens=MAX_TOKENS)
        if not r.choices:
            raise RuntimeError("the provider returned no choice (empty reply)")
        m = r.choices[0].message
        calls = []
        for c in m.tool_calls or []:
            try:
                args = json.loads(c.function.arguments or "{}")
            except ValueError:
                args = None                                   # the graph reports it to the model as an error
            calls.append({"id": c.id, "name": c.function.name, "arguments": args, "raw": c.function.arguments})
        u = r.usage
        t_in, t_out = (u.prompt_tokens, u.completion_tokens) if u else (0, 0)
        cost = getattr(u, "cost", None) if u else None          # OpenRouter reports what it charged
        return Reply(content=m.content or "", tool_calls=calls, tokens_in=t_in, tokens_out=t_out,
                     cost_usd=float(cost) if cost is not None else price(self.model, t_in, t_out),
                     latency_s=round(time.perf_counter() - started, 3), model=r.model or self.model)


class ScriptedLLM:
    """A fake model for tests. `policy(messages) -> (content, [(tool, args), ...])`."""

    def __init__(self, policy, model: str = "scripted"):
        self.policy, self.model, self.calls = policy, model, 0

    async def chat(self, messages: list[dict], tools: list[dict]) -> Reply:
        self.calls += 1
        content, calls = self.policy(messages)
        prompt = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages) // 4
        return Reply(content=content or "", model=self.model, tokens_in=prompt, tokens_out=20, latency_s=0.0,
                     tool_calls=[{"id": f"s{self.calls}_{i}", "name": n, "arguments": a, "raw": json.dumps(a)}
                                 for i, (n, a) in enumerate(calls)])


def get_llm(model: str | None = None):
    return OpenRouterLLM(model)
