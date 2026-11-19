"""Optional traces in Phoenix (Session 7): OpenTelemetry spans named with the OpenInference conventions.

OFF by default: unless TRACING=phoenix, every function here is a no-op and nothing heavy is imported, so the tests
and an evaluation without Phoenix run exactly as before.

    uv run phoenix serve                                   # another terminal; UI on http://localhost:6006
    $env:TRACING="phoenix"; uv run python eval/run_eval.py --only s004

One run = one tree: an AGENT span (runner.run_task) holding one LLM span per model call and one TOOL span per tool
call (graph.py, nodes `think` and `run_tool`).
"""
import json
import os
from contextlib import contextmanager

_tracer = None                       # set by setup(); None means tracing is off


def setup(project: str = "agent-demarches") -> bool:
    """Send spans to Phoenix if TRACING=phoenix ($PHOENIX_URL, default http://localhost:6006). True if on."""
    global _tracer
    if os.getenv("TRACING", "").strip().lower() != "phoenix":
        return False
    try:
        from phoenix.otel import register
    except ImportError:
        print("TRACING=phoenix, but arize-phoenix is not installed (uv sync): tracing stays off.")
        return False
    url = os.getenv("PHOENIX_URL", "http://localhost:6006").rstrip("/")
    provider = register(project_name=project, endpoint=url + "/v1/traces", batch=False, verbose=False)
    _tracer = provider.get_tracer("agent_demarches")
    print(f"Tracing to Phoenix: {url} (project {project})")
    return True


def _value(v):
    """OpenTelemetry attributes are str, int, float or bool: anything else goes as JSON."""
    return v if isinstance(v, (str, bool, int, float)) else json.dumps(v, ensure_ascii=False, default=str)


def set_attrs(span, **attrs) -> None:
    """Attributes with dots in their names are passed as **{"llm.model_name": ...}. None values are skipped."""
    if span is None:
        return
    for key, v in attrs.items():
        if v is not None:
            span.set_attribute(key, _value(v))


def error(span, message: str) -> None:
    if span is None:
        return
    from opentelemetry.trace import Status, StatusCode
    span.set_status(Status(StatusCode.ERROR, message))


@contextmanager
def span(name: str, kind: str, **attributes):
    """`with span("buy_tax_stamp", "TOOL", **{"tool.name": ...}) as s:` -- s is None when tracing is off."""
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as s:
        set_attrs(s, **{"openinference.span.kind": kind, **attributes})
        yield s
