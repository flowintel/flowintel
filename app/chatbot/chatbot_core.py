import asyncio
import logging
import os
import re
import threading
from urllib.parse import urlsplit

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import dspy
import litellm

from flask import current_app, session
from flask_login import current_user

from sqlalchemy.orm.exc import DetachedInstanceError

import conf.config_module as ConfigModule


# Suppress verbose output from DSPy / LiteLLM / httpx
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("dspy").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Debug-only flag to enable extra logging/messages from the MCP background launch.
# Set the environment variable FLOWINTEL_MCP_DEBUG=1 (or true/yes) to enable.
# Default is OFF so this doesn't change runtime behavior unless explicitly enabled.
_MCP_DEBUG = os.environ.get("FLOWINTEL_MCP_DEBUG", "").lower() in ("1", "true", "yes")

# When debugging MCP, ensure we have a console handler so logs are visible
if _MCP_DEBUG:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            logger.addHandler(ch)


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
_mcp_current_api_key: str = None
# Cancellation helpers for in-flight chatbot generations.
_chat_cancel_lock = threading.Lock()
# Map user_id -> cancellation callable
_chat_cancel_funcs = {}


async def _run_mcp_session(env: dict):
    global _mcp_session
    server_params = StdioServerParameters(command="flowintel-mcp", args=[], env=env)
    if _MCP_DEBUG:
        try:
            logger.debug("MCP debug: launching command=%s", server_params.command)
            logger.debug("MCP debug: FLOWINTEL_URL=%s", env.get("FLOWINTEL_URL"))
            logger.debug("MCP debug: FLOWINTEL_API_KEY present=%s", bool(env.get("FLOWINTEL_API_KEY")))
        except Exception:
            logger.exception("MCP debug: error while logging env info")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                _mcp_session = session
                if _MCP_DEBUG:
                    logger.debug("MCP debug: session initialized and ready")
                _mcp_ready.set()
                # Keep the session alive until the background thread is stopped
                await asyncio.Event().wait()
    except Exception as e:
        # Ensure the ready event is set so callers don't block indefinitely.
        logger.exception("MCP debug: exception while running MCP session: %s", e)
        _mcp_ready.set()


def _start_mcp_background(env: dict):
    global _mcp_loop
    _mcp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_mcp_loop)
    if _MCP_DEBUG:
        logger.debug("MCP debug: starting background asyncio loop in thread")
    try:
        _mcp_loop.run_until_complete(_run_mcp_session(env))
    except Exception:
        logger.exception("MCP debug: background loop terminated with exception")


def _ensure_mcp():
    """Start the MCP background thread if it is not already running.
    Must be called from within a Flask application context."""
    global _mcp_thread, _mcp_session, _mcp_loop, _mcp_current_api_key
    with _mcp_thread_lock:
        # Build env and resolve current user's API key without touching ORM-backed
        # attributes on the possibly-detached `current_user` object.
        env = {}
        env["FLOWINTEL_URL"] = (
            f'http://{current_app.config.get("FLOWINTEL_APP_HOST")}'
            f':{current_app.config.get("FLOWINTEL_APP_PORT")}/api'
        )

        api_key = None
        user_id = None

        # Try common Flask-Login session keys first to avoid accessing ORM attrs
        try:
            for key in ("_user_id", "user_id"):
                if key in session:
                    user_id = session.get(key)
                    break
            # If login manager set a custom key, try that too (import lazily)
            if not user_id:
                try:
                    from app import login_manager

                    lm_key = getattr(login_manager, "_user_id_key", None)
                    if lm_key and lm_key in session:
                        user_id = session.get(lm_key)
                except Exception:
                    # ignore import/call errors here
                    pass
        except Exception:
            # No request/session context or other session error
            user_id = None

        # Fallback to current_user.get_id() which may still raise, but try it last
        if not user_id and hasattr(current_user, "get_id"):
            try:
                user_id = current_user.get_id()
            except Exception:
                user_id = None

        # If we have an ID, reload the User from the DB to get a fresh instance
        if user_id:
            try:
                from app.db_class.db import load_user

                reloaded = load_user(user_id)
                if reloaded:
                    api_key = getattr(reloaded, "api_key", None)
            except Exception:
                logger.exception("MCP debug: failed to reload user from DB to obtain API key")
        else:
            # Last resort: try to read directly from current_user (may raise DetachedInstanceError)
            try:
                api_key = getattr(current_user, "api_key", None)
            except DetachedInstanceError:
                logger.exception("MCP debug: current_user is detached and no user id in session; cannot obtain API key")
            except Exception:
                logger.exception("MCP debug: unexpected error reading current_user.api_key")

        env["FLOWINTEL_API_KEY"] = api_key or ""

        # Export into process env so child processes inherit even if launcher doesn't merge
        try:
            if api_key:
                os.environ["FLOWINTEL_API_KEY"] = api_key
                if _MCP_DEBUG:
                    masked = api_key
                    if len(api_key) > 8:
                        masked = f"{api_key[:4]}...{api_key[-4:]}"
                    logger.debug("MCP debug: exported FLOWINTEL_API_KEY=%s", masked)
            else:
                os.environ.pop("FLOWINTEL_API_KEY", None)
        except Exception:
            logger.exception("MCP debug: unable to set FLOWINTEL_API_KEY in os.environ")

        # If an MCP thread is already running but the API key changed, restart it so
        # the MCP server inherits the new user's key.
        if _mcp_thread is not None and _mcp_thread.is_alive():
            if _mcp_current_api_key != env["FLOWINTEL_API_KEY"]:
                logger.info("MCP debug: API key changed for MCP; restarting background session")
                try:
                    if _mcp_loop:
                        _mcp_loop.call_soon_threadsafe(_mcp_loop.stop)
                    _mcp_thread.join(timeout=5)
                except Exception:
                    logger.exception("MCP debug: error while stopping existing MCP thread")
                finally:
                    try:
                        _mcp_session = None
                    except Exception:
                        pass
                    _mcp_thread = None

        if _mcp_thread is None or not _mcp_thread.is_alive():
            _mcp_ready.clear()
            _mcp_thread = threading.Thread(
                target=_start_mcp_background, args=(env,), daemon=True, name="mcp-session"
            )
            _mcp_thread.start()
            _mcp_current_api_key = env["FLOWINTEL_API_KEY"]

    _mcp_ready.wait(timeout=15)


# --- Sync wrappers around MCP tools (mirrors flowintel_dspy.py pattern) ---

# GET is not a read guarantee: several legacy API GET routes change state.
# Keep this list explicit so new endpoints are unavailable until reviewed.
_API_ID = r"(?:[0-9]+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
_READ_API_PATHS = {
    "GET": tuple(re.compile(pattern) for pattern in (
        r"/case/(?:all|completed|not_completed|get_taxonomies|get_galaxies|list_status|get_misp_object|get_misp_object_relationships|get_misp_attribute_types)",
        rf"/case/{_API_ID}(?:/(?:get_note|get_all_users|get_note_template|tasks|tasks_finished|all_notes|files|history|get_case_misp_object|get_case_misp_attributes))?",
        rf"/case/(?:get_taxonomies_case|get_galaxies_case)/{_API_ID}",
        r"/task/list_status",
        rf"/task/{_API_ID}(?:/(?:get_all_notes|get_note|files|get_taxonomies_task|get_galaxies_task|list_subtasks|list_urls_tools))?",
        rf"/task/{_API_ID}/(?:subtask|url_tool)/{_API_ID}",
        r"/templating/(?:cases|tasks)",
        rf"/templating/(?:case|task)/{_API_ID}",
        rf"/templating/case/{_API_ID}/task/{_API_ID}",
        rf"/templating/task/{_API_ID}/(?:case_templates|list_subtasks)",
        rf"/templating/task/{_API_ID}/subtask/{_API_ID}",
        rf"/templating/{_API_ID}/(?:list_urls_tools|url_tool/{_API_ID})",
        rf"/templating/(?:get_taxonomies_case|get_galaxies_case|get_taxonomies_task|get_galaxies_task)/{_API_ID}",
    )),
    "POST": (re.compile(r"/(?:case/(?:title|search|get_tags)|task/title|templating/case/title)"),),
}


def _chatbot_api_request(method, path):
    """Return the checked MCP method/path, or a refusal before starting MCP."""
    if not isinstance(method, str) or method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return None, None, "Refused: unsupported HTTP method"
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
        return None, None, "Refused: use a relative API path beginning with /"
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in path):
        return None, None, "Refused: invalid API path"
    try:
        parts = urlsplit(path)
    except ValueError:
        return None, None, "Refused: invalid API path"
    if parts.scheme or parts.netloc or parts.fragment or "#" in path:
        return None, None, "Refused: external URLs and fragments are not allowed"
    route = parts.path
    if any(char in route for char in ("%", "\\", ";")) or any(segment in ("", ".", "..") for segment in route[1:].split("/")):
        return None, None, "Refused: ambiguous API path"
    # MCP's configured base already ends in /api. Accept both Swagger-relative
    # paths and /api-prefixed paths, and forward only the checked representation.
    if route.startswith("/api/"):
        route = route[4:]
    if route.lower() == "/admin" or route.lower().startswith("/admin/"):
        return None, None, "Refused: admin endpoints are unavailable to the chatbot"
    if route == "/api" or route.startswith("/api/"):
        return None, None, "Refused: invalid API prefix"
    permitted_read = any(pattern.fullmatch(route) for pattern in _READ_API_PATHS.get(method, ()))
    if not permitted_read and getattr(ConfigModule, "CHATBOT_ALLOW_WRITES", False) is not True:
        return None, None, "Refused: this operation is not in the chatbot's read-only allow-list"
    return method, route + ("?" + parts.query if parts.query else ""), None


def call_api_wrapper(method: str, path: str, body: dict = None) -> str:
    """Read Flowintel cases, tasks and templates through reviewed API operations.
    Args: method (GET, or POST for searches), path (/case/... or /api/case/...),
    body (optional JSON). Other operations require administrator opt-in;
    admin endpoints are always unavailable."""
    method, path, refusal = _chatbot_api_request(method, path)
    if refusal:
        return refusal
    logger.debug("LLM requested tool -> %s %s", method, path)
    _ensure_mcp()
    coro = _mcp_session.call_tool("call_flowintel_api", {"method": method, "path": path, "body": body})
    future = asyncio.run_coroutine_threadsafe(coro, _mcp_loop)
    return str(future.result(timeout=30))


def get_docs_wrapper() -> str:
    """ALWAYS call this tool FIRST if you don't know the exact API paths or required payload.
    Returns the Swagger/OpenAPI documentation showing all valid endpoints."""
    logger.debug("LLM requested tool -> get_api_documentation")
    _ensure_mcp()
    coro = _mcp_session.call_tool("get_api_documentation", {})
    future = asyncio.run_coroutine_threadsafe(coro, _mcp_loop)
    return str(future.result(timeout=30))


# --- Register tools and build ReAct agent ---
flow_tool = dspy.Tool(call_api_wrapper)
docs_tool = dspy.Tool(get_docs_wrapper)
chatbot_module = dspy.ReAct(FlowintelQA, tools=[docs_tool, flow_tool])


def _get_ollama_base() -> str:
    """Return the Ollama base URL from config_module."""
    return getattr(ConfigModule, 'OLLAMA_URL', None) or "http://localhost:11434"


def configure_lm(model: str = None):
    """Configure (or reconfigure) the DSPy language model.

    Uses ConfigModule.OLLAMA_URL as the Ollama base URL.
    If *model* is provided the LM is always reconfigured with that model.
    Otherwise a one-time default configuration is applied.
    """
    global _dspy_configured

    with _dspy_config_lock:
        # Build kwargs for the requested (or default) model
        if model:
            # Use 'ollama_chat/' prefix for Ollama models with the DSPy LiteLLM backend
            full_model = model if "/" in model else f"ollama_chat/{model}"
        else:
            if _dspy_configured:
                return
            model_name = getattr(ConfigModule, 'OLLAMA_MODEL', None) or 'qwen3:0.6b'
            full_model = model_name if '/' in model_name else f'ollama_chat/{model_name}'

        api_key = getattr(ConfigModule, 'OLLAMA_KEY', None) or ""
        api_base = _get_ollama_base()

        kwargs = {"model": full_model}
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
                _dspy_configured = True
                return full_model
            raise
        return full_model


def _attempt_abort_lm_once():
    """Best-effort: try several common methods to abort/close the configured
    LM/client so an in-flight generation is interrupted. This is intentionally
    defensive since the concrete LM backend may expose different APIs.
    """
    try:
        lm_obj = None
        try:
            lm_obj = dspy.settings.lm
        except Exception:
            lm_obj = None

        if not lm_obj:
            return False

        # Try direct methods on the LM object
        for name in ("abort", "stop", "terminate", "close", "aclose", "cancel", "interrupt", "shutdown"):
            try:
                if hasattr(lm_obj, name):
                    getattr(lm_obj, name)()
                    logger.info("MCP debug: called %s() on LM object to abort generation", name)
                    return True
            except Exception:
                logger.exception("MCP debug: error calling %s() on LM object", name)

        # Try common nested attributes that may hold an HTTP client or transport
        for attr in ("client", "_client", "session", "_session", "transport", "httpx_client"):
            try:
                sub = getattr(lm_obj, attr, None)
                if not sub:
                    continue
                for name in ("abort", "stop", "terminate", "close", "aclose", "cancel", "interrupt", "shutdown"):
                    try:
                        if hasattr(sub, name):
                            getattr(sub, name)()
                            logger.info("MCP debug: called %s() on LM.%s to abort generation", name, attr)
                            return True
                    except Exception:
                        logger.exception("MCP debug: error calling %s() on LM.%s", name, attr)
            except Exception:
                logger.exception("MCP debug: error while inspecting LM.%s", attr)

        # As a last-ditch attempt, try litellm internal client if available
        try:
            import litellm
            client = getattr(litellm, "_client", None)
            if client:
                for name in ("abort", "stop", "terminate", "close", "aclose", "cancel", "interrupt", "shutdown"):
                    try:
                        if hasattr(client, name):
                            getattr(client, name)()
                            logger.info("MCP debug: called %s() on litellm._client to abort generation", name)
                            return True
                    except Exception:
                        logger.exception("MCP debug: error calling %s() on litellm._client", name)
        except Exception:
            pass

    except Exception:
        logger.exception("MCP debug: unexpected error in _attempt_abort_lm_once")
    return False


def register_chat_cancel(user_id, cancel_callable):
    """Register a cancellation callable for the given user_id."""
    with _chat_cancel_lock:
        if user_id is None:
            return
        _chat_cancel_funcs[str(user_id)] = cancel_callable


def clear_chat_cancel(user_id):
    with _chat_cancel_lock:
        try:
            _chat_cancel_funcs.pop(str(user_id), None)
        except Exception:
            pass


def cancel_current_generation(user_id=None) -> bool:
    """Attempt to cancel an in-flight generation for the given user.
    Returns True if a cancellation action was performed (best-effort).
    """
    with _chat_cancel_lock:
        key = str(user_id) if user_id is not None else None
        if key and key in _chat_cancel_funcs:
            try:
                func = _chat_cancel_funcs.get(key)
                if func:
                    func()
                # Also attempt a generic LM abort
                _attempt_abort_lm_once()
                # remove mapping
                _chat_cancel_funcs.pop(key, None)
                return True
            except Exception:
                logger.exception("MCP debug: exception while invoking cancel callable for user %s", key)
                return False
    # No specific mapping found, try a global LM abort
    return _attempt_abort_lm_once()


def get_chatbot_response(message: str, history: list = None, model: str = None, user_id: str = None) -> str:
    """Send a message to the DSPy chatbot and return the response.

    Args:
        message: The current user message.
        history: Optional list of previous messages as dicts with 'role' and 'content'.
        model:   Optional Ollama model name to use for this request.
    """
    configure_lm(model=model)
    # Resolve the display model name (strip ollama_chat/ prefix if present)
    lm_settings = dspy.settings.lm
    raw_model = getattr(lm_settings, 'model', '') if lm_settings else ''
    display_model = raw_model.split('/')[-1] if '/' in raw_model else raw_model
    # Register a per-user cancellation callable so external callers can stop
    # an in-flight generation. This is best-effort and may not always succeed
    # depending on the underlying LM backend.
    register_chat_cancel(user_id, lambda: _attempt_abort_lm_once())

    if history:
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history
        )
        full_question = f"Previous conversation:\n{history_text}\n\nUser: {message}"
    else:
        full_question = message
    try:
        result = chatbot_module(question=full_question)
        return result.answer, display_model
    finally:
        # Clean up cancel registration
        clear_chat_cancel(user_id)
