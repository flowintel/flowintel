import dspy
import json
import re
import threading
from flask import current_app
from flask_login import current_user


class FlowintelQA(dspy.Signature):
    """Answer questions as a helpful cybersecurity and incident response assistant for the Flowintel platform."""

    question: str = dspy.InputField(desc="The user's question")
    answer: str = dspy.OutputField(desc="A helpful and concise answer")


# module-level lock/flag for thread-safe dspy configuration
_dspy_config_lock = threading.Lock()
_dspy_configured = False


# --- FlowIntel action tools exposed to the ReAct agent ---
def _parse_payload(payload):
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    try:
        return json.loads(payload)
    except Exception:
        # treat as title string
        return {"title": str(payload)}


def _get_api_key():
    """Resolve an API key to use when calling internal REST APIs.

    Priority:
    1. `DSPY_TOOL_API_KEY` config
    2. `current_user.api_key` if available
    3. Bot user from `INIT_BOT_USER.email` -> lookup api_key in DB
    """
    # 1) explicit override in config
    api_key = current_app.config.get('DSPY_TOOL_API_KEY', "")
    if api_key:
        return api_key

    # 2) try the current logged-in user (preferred)
    try:
        if hasattr(current_user, 'api_key') and current_user.api_key:
            return current_user.api_key
    except RuntimeError:
        # no active request context or current_user not available
        pass

    # 3) fallback to INIT_BOT_USER email lookup
    bot_conf = current_app.config.get('INIT_BOT_USER') or {}
    bot_email = bot_conf.get('email')
    if bot_email:
        try:
            from ..db_class.db import User
            bot_user = User.query.filter_by(email=bot_email).first()
            if bot_user and getattr(bot_user, 'api_key', None):
                return bot_user.api_key
        except Exception:
            pass

    return None


def tool_create_case(payload: str) -> str:
    """Create a case. Payload: JSON or simple title string."""
    try:
        from ..case.CaseCore import CaseModel
    except Exception as e:
        return f"Error: cannot import CaseModel: {e}"

    form = _parse_payload(payload)
    title = form.get("title") or form.get("case_title")
    if not title:
        return "Error: 'title' is required to create a case"

    form_dict = {
        "title": title.strip(),
        "description": form.get("description", ""),
        "deadline_date": None,
        "deadline_time": None,
        "time_required": form.get("time_required", 0),
        "is_private": bool(form.get("is_private", False)),
        "ticket_id": form.get("ticket_id", ""),
        "tags": form.get("tags", []),
        "clusters": form.get("clusters", []),
        "custom_tags": form.get("custom_tags", []),
    }

    # Try to call the REST API endpoint instead of the core function
    api_key = _get_api_key()
    if not api_key:
        return "Error: no API key available to call internal API"

    try:
        # Use Flask test client to avoid external HTTP dependencies
        with current_app.test_client() as client:
            resp = client.post('/api/case/create', json=form_dict, headers={'X-API-KEY': api_key})
            data = resp.get_json(silent=True) or {}
            if resp.status_code in (200, 201):
                # API returns case_id and message
                cid = data.get('case_id') or data.get('case', {}).get('id')
                title = form_dict.get('title')
                return f"Case created via API: {title} (ID: {cid})"
            return f"API error creating case: {data.get('message') or resp.status_code}"
    except Exception as e:
        # Fallback: try direct core function if API call failed
        try:
            user = current_user
            case = CaseModel.create_case(form_dict, user)
            return f"Case created (fallback): {case.title} (ID: {case.id})"
        except Exception as e2:
            return f"Error creating case via API and fallback: {e}; {e2}"


def tool_list_cases(_payload: str = None) -> str:
    """Return a short list of open cases visible to the current user."""
    try:
        from ..case import common_core as CommonCaseModel
    except Exception as e:
        return f"Error: cannot import Case helpers: {e}"

    api_key = _get_api_key()
    if not api_key:
        return "Error: no API key available to call internal API"

    try:
        with current_app.test_client() as client:
            resp = client.get('/api/case/all', headers={'X-API-KEY': api_key})
            data = resp.get_json(silent=True) or {}
            if resp.status_code == 200 and 'cases' in data:
                cases = data['cases']
                if not cases:
                    return "No open cases found"
                lines = [f"{c.get('id')}: {c.get('title')}" for c in cases[:20]]
                return "\n".join(lines)
            return f"API error listing cases: {data.get('message') or resp.status_code}"
    except Exception as e:
        return f"Error listing cases via API: {e}"


def tool_create_task(payload: str) -> str:
    """Create a task in a case. Payload JSON must include 'case_id' and 'title'."""
    try:
        from ..case.TaskCore import TaskModel
        from ..case import common_core as CommonCaseModel
    except Exception as e:
        return f"Error: cannot import TaskModel: {e}"

    form = _parse_payload(payload)
    case_id = form.get("case_id") or form.get("cid")
    title = form.get("title")
    if not case_id or not title:
        return "Error: 'case_id' and 'title' are required to create a task"

    # Prefer calling an API endpoint to create tasks if available. There is no
    # dedicated API create-task endpoint in the codebase, so attempt a fallback
    # to the core function after verifying the case via the API.
    api_key = _get_api_key()
    case = None
    try:
        case = CommonCaseModel.get_case(case_id)
    except Exception:
        pass

    if api_key and case:
        try:
            with current_app.test_client() as client:
                # No dedicated task-create API; try to call case edit or other
                # endpoints are not appropriate. We'll fall back to core.
                pass
        except Exception:
            pass

    # Fallback: create task using core function
    try:
        user = current_user
        form_dict = {
            "title": title.strip(),
            "description": form.get("description", ""),
            "deadline_date": None,
            "deadline_time": None,
            "time_required": form.get("time_required", 0),
            "is_private": bool(form.get("is_private", False)),
            "tags": form.get("tags", []),
            "clusters": form.get("clusters", []),
            "custom_tags": form.get("custom_tags", []),
        }

        task = TaskModel.create_task(form_dict, case.id if case else case_id, user)
        if task:
            return f"Task created: {task.title} (ID: {task.id}) in case {task.case_id}"
        return "Error: task creation failed"
    except Exception as e:
        return f"Error creating task: {e}"


def tool_add_tag(payload: str) -> str:
    """Add a tag to a case. Payload can be JSON {case_id: <id>, tag: <name>} or a simple 'id:tag' string."""
    try:
        from ..case.CaseCore import CaseModel
        from ..case import common_core as CommonCaseModel
    except Exception as e:
        return f"Error: cannot import CaseModel: {e}"

    form = _parse_payload(payload)
    if not form.get("case_id"):
        if isinstance(payload, str) and ":" in payload:
            cid, tag = payload.split(":", 1)
            form = {"case_id": cid.strip(), "tag": tag.strip()}

    case_id = form.get("case_id")
    tag_name = form.get("tag") or form.get("tag_name")
    if not case_id or not tag_name:
        return "Error: 'case_id' and 'tag' required"

    api_key = _get_api_key()
    if not api_key:
        return "Error: no API key available to call internal API"

    try:
        with current_app.test_client() as client:
            # Get case JSON to preserve existing tags
            resp = client.get(f'/api/case/{case_id}', headers={'X-API-KEY': api_key})
            if resp.status_code != 200:
                data = resp.get_json(silent=True) or {}
                return f"API error fetching case: {data.get('message') or resp.status_code}"
            case_json = resp.get_json()
            tags = case_json.get('tags', []) if isinstance(case_json, dict) else []
            if tag_name not in tags:
                tags.append(tag_name)
            # Call edit endpoint with updated tags
            edit_resp = client.post(f'/api/case/{case_id}/edit', json={'tags': tags}, headers={'X-API-KEY': api_key})
            edit_data = edit_resp.get_json(silent=True) or {}
            if edit_resp.status_code in (200, 201):
                return f"Tag '{tag_name}' added to case {case_id} via API"
            return f"API error editing case: {edit_data.get('message') or edit_resp.status_code}"
    except Exception as e:
        # Fallback to core function
        try:
            case = CommonCaseModel.get_case(case_id)
            tag = CommonCaseModel.get_tag(tag_name)
            if not case:
                return f"Error: case {case_id} not found"
            if not tag:
                return f"Error: tag '{tag_name}' not found"
            CaseModel.add_tag(tag, case.id)
            return f"Tag '{tag_name}' added to case {case.id} (fallback)"
        except Exception as e2:
            return f"Error adding tag via API and fallback: {e}; {e2}"


# Register tools with DSPy ReAct (best-effort, with fallbacks)
_tools = []
if hasattr(dspy, "Tool"):
    try:
        _tools = [
            dspy.Tool(fn=tool_create_case, name="create_case", description="Create a case. Input: JSON or title"),
            dspy.Tool(fn=tool_list_cases, name="list_cases", description="List visible open cases"),
            dspy.Tool(fn=tool_create_task, name="create_task", description="Create a task in a case (JSON with case_id and title)"),
            dspy.Tool(fn=tool_add_tag, name="add_tag", description="Add a tag to a case (JSON or 'id:tag')"),
        ]
    except Exception:
        _tools = []

try:
    if _tools:
        chatbot_module = dspy.ReAct(FlowintelQA, tools=_tools)
    else:
        simple_tools = [
            tool_create_case,
            tool_list_cases,
            tool_create_task,
            tool_add_tag,
        ]
        try:
            chatbot_module = dspy.ReAct(FlowintelQA, tools=simple_tools)
        except Exception:
            chatbot_module = dspy.ReAct(FlowintelQA)
            if hasattr(dspy, "register_tool"):
                try:
                    for fn in simple_tools:
                        dspy.register_tool(fn.__name__, fn)
                except Exception:
                    pass
except Exception as e:
    print(e)
    chatbot_module = dspy.ReAct(FlowintelQA)


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

        model = current_app.config.get("DSPY_LM_MODEL", "ollama/qwen3:0.6b")
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


def get_chatbot_response(message: str) -> str:
    """Send a message to the DSPy chatbot and return the response."""
    configure_lm()
    result = chatbot_module(question=message)
    return result.answer
