"""Settings of the agentic part, in one place (paths, model, prices, guarded tools)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # src/agent_demarches/config.py -> repository root
SEEDS_DIR = ROOT / "seeds"
SERVERS_DIR = ROOT / "servers"
STATE_DIR = Path(os.getenv("AGENT_STATE_DIR", ROOT / "data" / "state"))   # live backend + memory (not versioned)

# --- the model -------------------------------------------------------------------------------
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "deepseek/deepseek-v4.1-flash")
MAX_TOKENS = 1500

# USD per million tokens (input, output). Used only when OpenRouter does not report `usage.cost`.
# Same convention as the Generative AI project: we never invent a price.
PRICES = {
    "deepseek/deepseek-v4.1-flash": (0.033, 0.080),
    "google/gemini-2.5-flash": (0.30, 2.50),
    "mistralai/mistral-small-2603": (0.15, 0.60),
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "qwen/qwen3-30b-a3b-instruct-2507": (0.08, 0.33),
}

# --- the guard (Session 3) -------------------------------------------------------------------
# Irreversible or costly writes: the graph stops on `approve` (interrupt) before running them.
NEEDS_APPROVAL = {"buy_tax_stamp", "cancel_appointment", "submit_application", "send_message"}
# Tools the model never sees: the graph calls list_facts itself, in the `recall` node.
HIDDEN_TOOLS = {"list_facts"}

# --- the dispatcher (Session 2) --------------------------------------------------------------
MAX_ATTEMPTS = 3            # one call + 2 retries, only for errors marked retryable
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "0.5"))   # seconds, doubled at each retry
