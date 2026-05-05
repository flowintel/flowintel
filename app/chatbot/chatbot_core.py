import asyncio
import logging
import os
import threading

from flask_login import current_user
import dspy
import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from flask import current_app

# Suppress verbose output from DSPy / LiteLLM / httpx
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("dspy").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class FlowintelQA(dspy.Signature):
    """Analyze and manage security cases using FlowIntel API tools."""

    question: str = dspy.InputField(desc="The user's question")
    answer: str = dspy.OutputField(desc="A helpful and concise answer")


# module-level lock/flag for thread-safe dspy configuration
_dspy_config_lock = threading.Lock()
_dspy_configured = False


# --- MCP session: persistent background asyncio event loop ---
_mcp_loop: asyncio.AbstractEventLoop = None
_mcp_session: ClientSession = None
_mcp_thread_lock = threading.Lock()
_mcp_thread: threading.Thread = None
_mcp_ready = threading.Event()


async def _run_mcp_session(env: dict):
    global _mcp_session
    server_params = StdioServerParameters(command="flowintel-mcp", args=[], env=env)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _mcp_session = session
            _mcp_ready.set()
            # Keep the session alive until the background thread is stopped
            await asyncio.Event().wait()


def _start_mcp_background(env: dict):
    global _mcp_loop
    _mcp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_mcp_loop)
    _mcp_loop.run_until_complete(_run_mcp_session(env))


def _ensure_mcp():
    """Start the MCP background thread if it is not already running.
    Must be called from within a Flask application context."""
    global _mcp_thread
    with _mcp_thread_lock:
        if _mcp_thread is None or not _mcp_thread.is_alive():
            # Capture config values here, while we still have an app context
            # env = dict(os.environ)
            env = dict()
            env["FLOWINTEL_URL"] = (
                f'http://{current_app.config.get("FLASK_URL")}'
                f':{current_app.config.get("FLASK_PORT")}/api'
            )
            env["FLOWINTEL_API_KEY"] = current_user.api_key
            _mcp_ready.clear()
            _mcp_thread = threading.Thread(
                target=_start_mcp_background, args=(env,), daemon=True, name="mcp-session"
            )
            _mcp_thread.start()
    _mcp_ready.wait(timeout=15)


# --- Sync wrappers around MCP tools (mirrors flowintel_dspy.py pattern) ---

def call_api_wrapper(method: str, path: str, body: dict = None) -> str:
    """Call the FlowIntel API via MCP. Args: method (GET/POST/...), path (/api/...), body (optional JSON dict)."""
    print(f"DEBUG: LLM requested tool -> {method} {path}...")
    _ensure_mcp()
    coro = _mcp_session.call_tool("call_flowintel_api", {"method": method, "path": path, "body": body})
    future = asyncio.run_coroutine_threadsafe(coro, _mcp_loop)
    return str(future.result(timeout=30))


def get_docs_wrapper() -> str:
    """ALWAYS call this tool FIRST if you don't know the exact API paths or required payload.
    Returns the Swagger/OpenAPI documentation showing all valid endpoints."""
    print("DEBUG: LLM requested tool -> get_api_documentation...")
    _ensure_mcp()
    coro = _mcp_session.call_tool("get_api_documentation", {})
    future = asyncio.run_coroutine_threadsafe(coro, _mcp_loop)
    return str(future.result(timeout=30))


# --- Register tools and build ReAct agent ---
flow_tool = dspy.Tool(call_api_wrapper)
docs_tool = dspy.Tool(get_docs_wrapper)
chatbot_module = dspy.ReAct(FlowintelQA, tools=[docs_tool, flow_tool])


def configure_lm():
    """Configure the DSPy language model from Flask app config in a thread-safe way.
    Avoid reconfiguring in other threads (dspy enforces settings change only by the
    thread that initially configured it)."""
    global _dspy_configured
    if _dspy_configured:
        return

    with _dspy_config_lock:
        if _dspy_configured:
            return

        # Use 'ollama_chat/' prefix for Ollama models with the DSPy LiteLLM backend
        model = current_app.config.get("DSPY_LM_MODEL", "ollama_chat/qwen3:0.6b")
        api_key = current_app.config.get("DSPY_LM_API_KEY", "")
        api_base = current_app.config.get("DSPY_LM_API_BASE", "http://localhost:11434")

        kwargs = {"model": model}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base

        lm = dspy.LM(**kwargs)
        try:
            dspy.configure(lm=lm)
            _dspy_configured = True
        except Exception as e:
            msg = str(e).lower()
            if "dspy.settings can only be changed" in msg or "can only be changed by the thread" in msg:
                # Another thread already configured dspy; consider configured.
                _dspy_configured = True
                return
            raise


def get_chatbot_response(message: str, history: list = None) -> str:
    """Send a message to the DSPy chatbot and return the response.

    Args:
        message: The current user message.
        history: Optional list of previous messages as dicts with 'role' and 'content'.
    """
    configure_lm()
    if history:
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history
        )
        full_question = f"Previous conversation:\n{history_text}\n\nUser: {message}"
    else:
        full_question = message
    result = chatbot_module(question=full_question)
    return result.answer
