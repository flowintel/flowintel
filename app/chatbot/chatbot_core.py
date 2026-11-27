import asyncio
import logging
import os
import re
from urllib.parse import urlsplit

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import dspy
import litellm

from flask import current_app, session
from flask_login import current_user
from redis.exceptions import RedisError

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


GENERATION_TIMEOUT_SECONDS = 150


class GenerationTimedOut(TimeoutError):
    pass


class GenerationStopped(Exception):
    pass


def _mcp_environment():
    """Resolve credentials from the authenticated request, including detached users."""
    from app import login_manager
    from app.db_class.db import load_user

    user_id = None
    for key in ("_user_id", "user_id", getattr(login_manager, "_user_id_key", None)):
        if key and session.get(key):
            user_id = session[key]
            break
    if not user_id:
        user_id = current_user.get_id()

    user = load_user(user_id)
    if user is None or not user.api_key:
        raise RuntimeError("Authenticated chatbot API identity is unavailable")
    return {
        "FLOWINTEL_URL": (
            f'http://{current_app.config.get("FLOWINTEL_APP_HOST")}'
            f':{current_app.config.get("FLOWINTEL_APP_PORT")}/api'
        ),
        "FLOWINTEL_API_KEY": user.api_key,
    }


async def _call_mcp_tool(env, name, arguments):
    """Own the identity, transport and cleanup for exactly one tool invocation."""
    tool_timeout = current_app.config["CHATBOT_TOOL_TIMEOUT"]
    server_params = StdioServerParameters(command="flowintel-mcp", args=[], env=env)
    async with asyncio.timeout(15) as startup_timeout:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                startup_timeout.reschedule(None)
                return await asyncio.wait_for(client.call_tool(name, arguments), timeout=tool_timeout)


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


async def call_api_wrapper(method: str, path: str, body: dict | None = None) -> str:
    """Read Flowintel cases, tasks and templates through reviewed API operations.
    Args: method (GET, or POST for searches), path (/case/... or /api/case/...),
    body (optional JSON). Other operations require administrator opt-in;
    admin endpoints are always unavailable."""
    method, path, refusal = _chatbot_api_request(method, path)
    if refusal:
        return refusal
    logger.debug("LLM requested tool -> %s %s", method, path)
    arguments = {"method": method, "path": path}
    if body is not None:
        arguments["body"] = body
    return str(await _call_mcp_tool(_mcp_environment(), "call_flowintel_api", arguments))


async def get_docs_wrapper() -> str:
    """ALWAYS call this tool FIRST if you don't know the exact API paths or required payload.
    Returns the Swagger/OpenAPI documentation showing all valid endpoints."""
    logger.debug("LLM requested tool -> get_api_documentation")
    return str(await _call_mcp_tool(_mcp_environment(), "get_api_documentation", {}))


# --- Register tools and build ReAct agent ---
flow_tool = dspy.Tool(call_api_wrapper)
docs_tool = dspy.Tool(get_docs_wrapper)
chatbot_module = dspy.ReAct(FlowintelQA, tools=[docs_tool, flow_tool])


def _get_ollama_base() -> str:
    """Return the Ollama base URL from config_module."""
    return getattr(ConfigModule, 'OLLAMA_URL', None) or "http://localhost:11434"


def _create_lm(model):
    """Create a language model owned by a single chatbot request."""
    model_name = model or getattr(ConfigModule, "OLLAMA_MODEL", None) or "qwen3:0.6b"
    full_model = model_name if "/" in model_name else f"ollama_chat/{model_name}"
    kwargs = {"model": full_model, "api_base": _get_ollama_base()}
    api_key = getattr(ConfigModule, "OLLAMA_KEY", None)
    if api_key:
        kwargs["api_key"] = api_key
    return dspy.LM(**kwargs)


def _cancellation_key(user_id, request_id):
    return f"chatbot:stop:{user_id}:{request_id}"


def cancel_current_generation(user_id, request_id):
    """Signal the worker handling this user's request through shared Valkey."""
    current_app.config["SESSION_REDIS"].set(
        _cancellation_key(user_id, request_id), "1", ex=GENERATION_TIMEOUT_SECONDS + 30
    )


async def _wait_for_stop(redis_client, key):
    try:
        while not await asyncio.to_thread(redis_client.exists, key):
            await asyncio.sleep(0.5)
    except RedisError:
        logger.warning("Could not check for a chatbot stop request", exc_info=True)
        return False
    return True


async def _generate_with_stop(question, redis_client, key):
    try:
        # The Stop request can reach its worker before /ask starts generation.
        if await asyncio.to_thread(redis_client.exists, key):
            raise GenerationStopped
    except RedisError:
        logger.warning("Could not check for a chatbot stop request", exc_info=True)
        return await chatbot_module.acall(question=question)

    generation = asyncio.create_task(chatbot_module.acall(question=question))
    stop = asyncio.create_task(_wait_for_stop(redis_client, key))
    try:
        done, _ = await asyncio.wait((generation, stop), return_when=asyncio.FIRST_COMPLETED)
        if stop in done and stop.result():
            raise GenerationStopped
        return await generation
    finally:
        generation.cancel()
        stop.cancel()
        await asyncio.gather(generation, stop, return_exceptions=True)


async def _generate(question, model, user_id, request_id):
    lm = _create_lm(model)
    deadline = asyncio.timeout(GENERATION_TIMEOUT_SECONDS)
    try:
        with dspy.context(lm=lm):
            async with deadline:
                redis_client = current_app.config.get("SESSION_REDIS")
                if redis_client is None or request_id is None:
                    result = await chatbot_module.acall(question=question)
                else:
                    result = await _generate_with_stop(question, redis_client, _cancellation_key(user_id, request_id))
    except TimeoutError as exc:
        if deadline.expired():
            raise GenerationTimedOut from exc
        raise
    finally:
        # DSPy 3.2 does not expose the per-LM cleanup hook available in 3.4.
        aclose = getattr(lm, "aclose", None)
        if aclose is not None:
            await aclose()

    return result.answer, lm.model.rsplit("/", 1)[-1]


def get_chatbot_response(message, history=None, model=None, user_id=None, request_id=None):
    """Answer a question within the deadline for the entire ReAct run."""
    if history:
        history_text = "\n".join(
            f"{'User' if entry['role'] == 'user' else 'Assistant'}: {entry['content']}"
            for entry in history
        )
        message = f"Previous conversation:\n{history_text}\n\nUser: {message}"
    return asyncio.run(_generate(message, model, user_id, request_id))
