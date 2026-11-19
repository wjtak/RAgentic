"""Tracing is off by default: without TRACING=phoenix nothing is sent, and the spans are no-ops."""
import os
import subprocess
import sys

from agent_demarches import tracing


def test_tracing_is_a_no_op_by_default(monkeypatch):
    monkeypatch.delenv("TRACING", raising=False)
    monkeypatch.setattr(tracing, "_tracer", None)
    assert tracing.setup() is False
    with tracing.span("buy_tax_stamp", "TOOL", **{"tool.name": "buy_tax_stamp", "input.value": {"x": 1}}) as s:
        assert s is None
        tracing.set_attrs(s, **{"output.value": {"ok": True}})          # no-ops on None, no error
        tracing.error(s, "boom")


def test_tracing_off_imports_nothing_heavy():
    # in a fresh interpreter: pytest itself loads a phoenix plugin (arize-phoenix-client), so check outside it
    code = ("import sys; from agent_demarches import tracing; tracing.setup()\n"
            "with tracing.span('x', 'AGENT'): pass\n"
            "assert not any(m.split('.')[0] in ('phoenix', 'opentelemetry') for m in sys.modules), 'heavy import'")
    env = {k: v for k, v in os.environ.items() if k != "TRACING"}
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
