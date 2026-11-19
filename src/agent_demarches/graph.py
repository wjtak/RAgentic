"""The agent, as a LangGraph state machine (Session 3), with long-term memory (Session 4).

    START -> recall -> think -> router -> run_tool  -> think          (the loop)
                                     \\-> approve  -> run_tool | think   (dangerous tool: interrupt(), a human decides)
                                     \\-> ask_human -> think             (ambiguous request: interrupt(), a question)
                                     \\-> give_up  -> END                (step budget spent: stop_reason max_steps)
                                     \\-> END                            (final answer: stop_reason answered)

- One step = one model call. `max_steps` bounds the model calls; the last one must be an answer.
- One tool call per step (as in Session 3): the history is rebuilt from `observations`, so the checkpoint is the
  whole memory of the run, and a run paused on `approve` can be resumed in another process.
- The guard does not trust the model: every tool in NEEDS_APPROVAL goes through `approve`, whatever the prompt says.
"""
import json
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agent_demarches import memory, tracing
from agent_demarches.config import NEEDS_APPROVAL
from agent_demarches.prompts import ASK_USER, SYSTEM


class AgentState(TypedDict, total=False):
    task: str
    today: str
    run_id: str                                          # the idempotency keys are derived from it
    max_steps: int
    steps: int                                           # model calls so far
    facts: str                                           # long-term memory, read once by `recall`
    action: dict                                         # the model's last decision
    observations: Annotated[list, operator.add]          # one per tool call that reached the model (reducer: append)
    events: Annotated[list, operator.add]                # the trace: model calls, chosen calls, approvals
    answer: str | None
    stop_reason: str | None                              # answered | asked_user | max_steps | error


def as_decision(value) -> dict:
    """A human decision may come as a dict, a bool or text ("yes", '{"approve": true}'): normalise it."""
    if isinstance(value, dict):
        return {"approve": bool(value.get("approve")), "reason": str(value.get("reason", ""))}
    if isinstance(value, bool):
        return {"approve": value, "reason": ""}
    text = str(value).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, (dict, bool)):
            return as_decision(parsed)
    except ValueError:
        pass
    return {"approve": text.lower() in {"true", "yes", "y", "oui", "ok", "approve"}, "reason": text}


def build_messages(state: AgentState) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM.format(today=state["today"], facts=state.get("facts") or "(none)")},
            {"role": "user", "content": state["task"]}]
    for i, o in enumerate(state.get("observations", [])):
        call_id = f"c{i}"
        msgs.append({"role": "assistant", "content": o.get("thought") or None, "tool_calls": [{
            "id": call_id, "type": "function",
            "function": {"name": o["tool"], "arguments": json.dumps(o["args"] or {}, ensure_ascii=False)}}]})
        payload = o["result"] if o["ok"] else {"error": o["error"]}
        msgs.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(payload, ensure_ascii=False)})
    return msgs


def build_graph(hub, llm, checkpointer=None, needs_approval=frozenset(NEEDS_APPROVAL)):
    """`hub`: a ToolHub (MCP servers), `llm`: OpenRouterLLM or ScriptedLLM. Returns the compiled graph."""
    tools = hub.openai_specs() + [ASK_USER]

    async def recall(state: AgentState) -> dict:
        """Session 4: read the long-term memory once, before the first model call."""
        res = await hub.call("list_facts", {}, state["run_id"])
        facts = memory.as_prompt(res["result"]) if res["ok"] else "(memory unavailable)"
        return {"facts": facts, "steps": 0, "answer": None, "stop_reason": None,
                "events": [{"kind": "recall", "facts": facts}]}

    async def think(state: AgentState) -> dict:
        n = state["steps"] + 1
        with tracing.span(f"llm step {n}", "LLM", **{"llm.model_name": llm.model}) as s:
            reply = await llm.chat(build_messages(state), tools)
            said = [{c["name"]: c["arguments"]} for c in reply.tool_calls] or reply.content
            tracing.set_attrs(s, **{"llm.token_count.prompt": reply.tokens_in,
                                    "llm.token_count.completion": reply.tokens_out, "output.value": said})
        event = {"kind": "model", "step": n, "content": reply.content, "model": reply.model,
                 "tool_calls": [c["name"] for c in reply.tool_calls], "tokens_in": reply.tokens_in,
                 "tokens_out": reply.tokens_out, "cost_usd": reply.cost_usd, "latency_s": reply.latency_s}
        if not reply.tool_calls:
            return {"steps": n, "action": {"type": "final"}, "answer": reply.content, "stop_reason": "answered",
                    "events": [event]}
        call = reply.tool_calls[0]                       # one call per step, even if the model sent several
        kind = "ask" if call["name"] == "ask_user" else "call"
        action = {"type": kind, "tool": call["name"], "args": call["arguments"], "raw": call["raw"],
                  "thought": reply.content, "step": n}
        return {"steps": n, "action": action, "events": [event, {
            "kind": "call", "step": n, "tool": call["name"], "args": call["arguments"],
            "dropped": [c["name"] for c in reply.tool_calls[1:]]}]}

    def router(state: AgentState) -> str:
        action = state["action"]
        if action["type"] == "final":
            return END
        if state["steps"] >= state["max_steps"]:
            return "give_up"
        if action["type"] == "ask":
            return "ask_human"
        if action["tool"] in needs_approval:
            return "approve"
        return "run_tool"

    def approve(state: AgentState) -> Command:
        """Session 3: pause before an irreversible action. Nothing runs before interrupt(): it is replayed on resume."""
        a = state["action"]
        decision = as_decision(interrupt({"type": "approval", "tool": a["tool"], "args": a["args"],
                                          "plan": a.get("thought") or ""}))
        event = {"kind": "approval", "step": a["step"], "tool": a["tool"], "args": a["args"], **decision}
        if decision["approve"]:
            return Command(goto="run_tool", update={"events": [event]})
        rejected = {"tool": a["tool"], "args": a["args"], "thought": a.get("thought"), "step": a["step"], "ok": False,
                    "executed": False, "error": {"code": "rejected_by_user", "retryable": False,
                    "message": f"The user rejected this action ({decision['reason'] or 'no reason given'}). "
                               "Do not retry it and do not work around it."}}
        return Command(goto="think", update={"events": [event], "observations": [rejected]})

    def ask_human(state: AgentState) -> Command:
        a = state["action"]
        question = (a["args"] or {}).get("question", "")
        answer = interrupt({"type": "question", "question": question})
        obs = {"tool": "ask_user", "args": {"question": question}, "thought": a.get("thought"), "step": a["step"],
               "ok": True, "executed": True, "result": {"user_answer": str(answer)}}
        return Command(goto="think", update={"observations": [obs]})

    async def run_tool(state: AgentState) -> dict:
        a = state["action"]
        base = {"tool": a["tool"], "args": a["args"], "thought": a.get("thought"), "step": a["step"]}
        if a["args"] is None:                            # the model wrote invalid JSON: tell it, run nothing
            return {"observations": [{**base, "ok": False, "executed": False, "error": {
                "code": "invalid_json", "message": f"Arguments are not valid JSON: {str(a['raw'])[:200]}"}}]}
        with tracing.span(a["tool"], "TOOL", **{"tool.name": a["tool"], "input.value": a["args"]}) as s:
            res = await hub.call(a["tool"], a["args"], state["run_id"])
            tracing.set_attrs(s, **{"output.value": res["result"] if res["ok"] else res["error"]})
            if not res["ok"]:
                tracing.error(s, str(res["error"].get("code", "tool_error")))
        obs = {**base, "ok": res["ok"], "executed": True, "attempts": res["attempts"], "latency_s": res["latency_s"],
               "retried_errors": [e.get("code") for e in res.get("errors", [])]}
        obs["result" if res["ok"] else "error"] = res["result"] if res["ok"] else res["error"]
        return {"observations": [obs]}

    def give_up(state: AgentState) -> dict:
        return {"stop_reason": "max_steps", "answer": None,
                "events": [{"kind": "stop", "reason": "max_steps", "step": state["steps"]}]}

    g = StateGraph(AgentState)
    g.add_node("recall", recall)
    g.add_node("think", think)
    g.add_node("run_tool", run_tool)
    g.add_node("approve", approve, destinations=("run_tool", "think"))
    g.add_node("ask_human", ask_human, destinations=("think",))
    g.add_node("give_up", give_up)
    g.add_edge(START, "recall")
    g.add_edge("recall", "think")
    g.add_conditional_edges("think", router, {"run_tool": "run_tool", "approve": "approve", "ask_human": "ask_human",
                                              "give_up": "give_up", END: END})
    g.add_edge("run_tool", "think")
    g.add_edge("give_up", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
