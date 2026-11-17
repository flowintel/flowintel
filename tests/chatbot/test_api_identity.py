import asyncio
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
import sys
import threading
from types import SimpleNamespace

import pytest
from flask import session
from flask.sessions import SecureCookieSessionInterface
from flask_login import current_user

from app import db
from app.chatbot import chatbot_core as Chatbot
from app.db_class.db import Case, User


@pytest.fixture
def identities(app):
    with app.app_context():
        users = {key: User.query.filter_by(api_key=key + "_api_key").one() for key in ("editor", "admin")}
        now = datetime.now(timezone.utc)
        case = Case(title="PRIVATE ADMIN INVESTIGATION", description="Private evidence", is_private=True,
                    creation_date=now, last_modif=now)
        db.session.add(case)
        db.session.commit()
        return {"tokens": {key: user.get_id() for key, user in users.items()}, "case": case.id}


@pytest.fixture
def transport(app, monkeypatch):
    state = {"calls": [], "opened": [], "closed": [], "hold_editor": False, "hold_after": 0,
             "editor_initializations": 0, "failure": None, "hang": None,
             "editor_started": threading.Event(), "release_editor": threading.Event()}

    @asynccontextmanager
    async def stdio(params):
        identity = dict(params.env)
        state["opened"].append(identity)
        try:
            if state["failure"] == "stdio":
                raise RuntimeError("Synthetic transport failure")
            if state["hang"] == "stdio":
                await asyncio.Event().wait()
            yield identity, None
        finally:
            state["closed"].append(identity)

    class Session:
        def __init__(self, read, write):
            self.identity = read

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def initialize(self):
            if state["failure"] == "initialize":
                raise RuntimeError("Synthetic initialization failure")
            if state["hang"] == "initialize":
                await asyncio.Event().wait()
            if self.identity["FLOWINTEL_API_KEY"] == "editor_api_key":
                state["editor_initializations"] += 1
                if state["hold_editor"] and state["editor_initializations"] > state["hold_after"]:
                    state["editor_started"].set()
                    while not state["release_editor"].is_set():
                        await asyncio.sleep(0.001)

        async def call_tool(self, name, args):
            key = self.identity["FLOWINTEL_API_KEY"]
            state["calls"].append((key, name, args))
            if state["failure"] == "tool":
                raise RuntimeError("Synthetic tool failure")
            if state["hang"] == "tool":
                await asyncio.Event().wait()
            if name == "get_api_documentation":
                return "API documentation"
            return json.dumps({"api_key": key})

    monkeypatch.setattr(Chatbot, "stdio_client", stdio)
    monkeypatch.setattr(Chatbot, "ClientSession", Session)
    yield state
    state["release_editor"].set()
    assert len(state["closed"]) == len(state["opened"])


def invoke(app, identities, who, docs=False):
    with app.test_request_context("/chatbot/ask"):
        session["_user_id"] = identities["tokens"][who]
        if docs:
            return Chatbot.get_docs_wrapper()
        return Chatbot.call_api_wrapper("GET", f"/case/{identities['case']}")


@pytest.mark.parametrize("editor_docs,admin_docs", [(False, False), (True, False), (False, True), (True, True)])
def test_overlapping_tools_keep_their_authenticated_identity(app, identities, transport, editor_docs, admin_docs):
    transport["hold_editor"] = True
    results, errors = {}, []

    def run(who, docs):
        try:
            results[who] = invoke(app, identities, who, docs)
        except Exception as error:
            errors.append(error)

    editor = threading.Thread(target=run, args=("editor", editor_docs))
    admin = threading.Thread(target=run, args=("admin", admin_docs))
    editor.start()
    try:
        assert transport["editor_started"].wait(5)
        admin.start()
        admin.join(timeout=10)
        assert not admin.is_alive()
    finally:
        transport["release_editor"].set()
        editor.join(timeout=10)
    assert not editor.is_alive() and not errors
    assert Counter(call[0] for call in transport["calls"]) == Counter({"editor_api_key": 1, "admin_api_key": 1})
    if not editor_docs:
        with app.test_client() as client:
            response = client.get(f"/api/case/{identities['case']}",
                                  headers={"X-API-KEY": json.loads(results["editor"])["api_key"]})
            assert response.status_code == 403
            assert "PRIVATE ADMIN INVESTIGATION" not in response.get_data(as_text=True)
    if not admin_docs:
        assert json.loads(results["admin"])["api_key"] == "admin_api_key"


def test_authorized_single_tool_uses_browser_identity(app, identities, transport):
    result = invoke(app, identities, "admin")
    with app.test_client() as client:
        response = client.get(f"/api/case/{identities['case']}",
                              headers={"X-API-KEY": json.loads(result)["api_key"]})
        assert response.status_code == 200
        assert response.json["title"] == "PRIVATE ADMIN INVESTIGATION"
    assert transport["calls"][0][0] == "admin_api_key"


@pytest.mark.parametrize("credential", [None, "ambient-admin-key"])
def test_tools_do_not_change_parent_process_credentials(app, identities, transport, monkeypatch, credential):
    if credential:
        monkeypatch.setenv("FLOWINTEL_API_KEY", credential)
    else:
        monkeypatch.delenv("FLOWINTEL_API_KEY", raising=False)
    invoke(app, identities, "editor")
    invoke(app, identities, "admin", docs=True)
    assert os.environ.get("FLOWINTEL_API_KEY") == credential
    assert [env["FLOWINTEL_API_KEY"] for env in transport["opened"]] == ["editor_api_key", "admin_api_key"]


@pytest.mark.parametrize("invalid", ["anonymous", "numeric", "bad_token", "deleted", "password_changed", "missing_key"])
def test_invalid_identity_cannot_fall_back_to_ambient_credentials(app, identities, transport, monkeypatch, invalid):
    monkeypatch.setenv("FLOWINTEL_API_KEY", "ambient-admin-key")
    with app.test_request_context("/chatbot/ask"):
        if invalid != "anonymous":
            session["_user_id"] = identities["tokens"]["editor"]
        if invalid == "numeric":
            session["_user_id"] = identities["tokens"]["editor"].split(":")[0]
        elif invalid == "bad_token":
            session["_user_id"] = "2:" + "0" * 64
        elif invalid in {"deleted", "password_changed", "missing_key"}:
            user = User.query.filter_by(api_key="editor_api_key").one()
            if invalid == "deleted":
                db.session.delete(user)
            elif invalid == "password_changed":
                user.password_hash = "Changed password invalidates the login"
            else:
                user.api_key = None
            db.session.commit()
        for tool in (lambda: Chatbot.call_api_wrapper("GET", "/case/all"), Chatbot.get_docs_wrapper):
            with pytest.raises(RuntimeError, match="identity is unavailable"):
                tool()
    assert transport["opened"] == []
    assert os.environ["FLOWINTEL_API_KEY"] == "ambient-admin-key"


def test_detached_user_and_key_rotation_keep_current_identity(app, identities, transport):
    with app.test_request_context("/chatbot/ask"):
        session["_user_id"] = identities["tokens"]["editor"]
        assert current_user.id
        db.session.remove()
        Chatbot.get_docs_wrapper()
        user = User.query.filter_by(api_key="editor_api_key").one()
        user.api_key = "rotated-editor-key"
        db.session.commit()
        db.session.remove()
        Chatbot.call_api_wrapper("GET", "/case/all")
    assert [call[0] for call in transport["calls"]] == ["editor_api_key", "rotated-editor-key"]


@pytest.mark.parametrize("stage", ["stdio", "initialize", "tool"])
def test_failed_tool_closes_its_transport_and_does_not_poison_next_user(app, identities, transport, stage):
    transport["failure"] = stage
    with pytest.raises(RuntimeError, match="Synthetic"):
        invoke(app, identities, "admin")
    assert len(transport["closed"]) == 1
    transport["failure"] = None
    invoke(app, identities, "editor")
    assert transport["calls"][-1][0] == "editor_api_key"


@pytest.mark.parametrize("stage", ["stdio", "initialize", "tool"])
def test_timeout_closes_only_its_owned_transport(app, identities, transport, monkeypatch, stage):
    transport["hang"] = stage
    original_wait = asyncio.wait_for
    original_timeout = asyncio.timeout

    async def short_wait(awaitable, timeout):
        return await original_wait(awaitable, timeout=0.01)

    monkeypatch.setattr(Chatbot.asyncio, "wait_for", short_wait)
    monkeypatch.setattr(Chatbot.asyncio, "timeout", lambda delay: original_timeout(0.01))
    with pytest.raises(TimeoutError):
        invoke(app, identities, "admin")
    assert len(transport["closed"]) == 1
    transport["hang"] = None
    invoke(app, identities, "editor", docs=True)
    assert transport["calls"][-1][0] == "editor_api_key"


@pytest.mark.parametrize("method,path", [
    ("GET", "/admin/users"), ("GET", "/case/1/delete"), ("POST", "/case/create"),
    ("GET", "https://attacker.invalid/case/all"), ("GET", "/case/%31"),
    ("GET", "/case/../admin/users"), ("GET", "/case/all#fragment"),
])
def test_existing_tool_restrictions_refuse_before_opening_transport(app, transport, monkeypatch, method, path):
    monkeypatch.setattr(Chatbot.ConfigModule, "CHATBOT_ALLOW_WRITES", False, raising=False)
    with app.test_request_context("/chatbot/ask"):
        assert Chatbot.call_api_wrapper(method, path).startswith("Refused:")
    assert not transport["opened"]


def test_explicit_writes_keep_actor_and_admin_endpoints_remain_blocked(app, identities, transport, monkeypatch):
    monkeypatch.setattr(Chatbot.ConfigModule, "CHATBOT_ALLOW_WRITES", True, raising=False)
    with app.test_request_context("/chatbot/ask"):
        session["_user_id"] = identities["tokens"]["editor"]
        result = Chatbot.call_api_wrapper("POST", "/api/case/create", {"api_key": "admin_api_key", "title": "Case"})
        assert json.loads(result)["api_key"] == "editor_api_key"
        assert Chatbot.call_api_wrapper("POST", "/api/admin/add_user", {}).startswith("Refused:")
    assert len(transport["calls"]) == 1
    assert transport["calls"][0][2]["path"] == "/case/create"


def test_ask_route_keeps_browser_identity_after_session_removal(app, identities, transport, monkeypatch):
    from app.chatbot.chatbot import chatbot_blueprint
    from app.db_class.db import ChatConversation, ChatMessage

    app.register_blueprint(chatbot_blueprint, url_prefix="/chatbot")
    app.session_interface = SecureCookieSessionInterface()
    monkeypatch.setitem(app.config, "SESSION_REDIS", None)
    monkeypatch.setitem(app.config, "ENABLE_CHATBOT", True)
    monkeypatch.setattr(Chatbot, "configure_lm", lambda model=None: None)

    def agent(question):
        Chatbot.get_docs_wrapper()
        return SimpleNamespace(answer=Chatbot.call_api_wrapper("GET", f"/case/{identities['case']}"))

    monkeypatch.setattr(Chatbot, "chatbot_module", agent)
    with app.test_client() as client:
        with client.session_transaction() as browser_session:
            browser_session["_user_id"] = identities["tokens"]["editor"]
            browser_session["_fresh"] = True
        response = client.post("/chatbot/ask", headers={"X-API-KEY": "admin_api_key"},
                               json={"message": "Read this case", "user_id": 1, "api_key": "admin_api_key"})
        assert response.status_code == 200
        assert json.loads(response.json["response"])["api_key"] == "editor_api_key"
        conversation_id = response.json["conversation_id"]
        history = client.get(f"/chatbot/conversation/{conversation_id}")
        assert [message["role"] for message in history.json["messages"]] == ["user", "assistant"]
    assert all(call[0] == "editor_api_key" for call in transport["calls"])
    with app.app_context():
        assert ChatConversation.query.count() == 1 and ChatMessage.query.count() == 2


@pytest.mark.parametrize("who", ["editor", "admin"])
def test_real_stdio_transport_keeps_explicit_child_identity(app, identities, monkeypatch, who):
    # Exercise the installed MCP client/stdio lifecycle without an LLM or network service.
    server_source = '''
import os
from mcp.server.fastmcp import FastMCP
server = FastMCP("Identity test")
@server.tool()
def call_flowintel_api(method: str, path: str, body: dict | None = None) -> str:
    return os.environ["FLOWINTEL_API_KEY"]
server.run(transport="stdio")
'''
    parameters = Chatbot.StdioServerParameters

    def test_server(command, args, env):
        return parameters(command=sys.executable, args=["-c", server_source], env=env)

    monkeypatch.setattr(Chatbot, "StdioServerParameters", test_server)
    monkeypatch.setenv("FLOWINTEL_API_KEY", "ambient-wrong-key")
    result = invoke(app, identities, who)
    assert who + "_api_key" in result
    assert "ambient-wrong-key" not in result
    assert os.environ["FLOWINTEL_API_KEY"] == "ambient-wrong-key"


def test_real_react_dispatch_keeps_concurrent_api_identities(app, identities, transport, monkeypatch):
    # Replace only the LLM predictions; keep the actual ReAct loop and registered tools.
    def next_step(**inputs):
        trajectory = inputs["trajectory"]
        if "tool_name_0" not in trajectory:
            name, args = "get_docs_wrapper", {}
        elif "tool_name_1" not in trajectory:
            name, args = "call_api_wrapper", {"method": "GET", "path": f"/case/{identities['case']}"}
        else:
            name, args = "finish", {}
        return SimpleNamespace(next_thought="Deterministic test plan", next_tool_name=name, next_tool_args=args)

    monkeypatch.setattr(Chatbot, "configure_lm", lambda model=None: None)
    monkeypatch.setattr(Chatbot.chatbot_module, "react", next_step)
    monkeypatch.setattr(Chatbot.chatbot_module, "extract", lambda **inputs: {"answer": inputs["trajectory"]})
    transport["hold_editor"] = True
    transport["hold_after"] = 1
    results, errors = {}, []

    def run(who):
        try:
            with app.test_request_context("/chatbot/ask"):
                session["_user_id"] = identities["tokens"][who]
                results[who] = Chatbot.get_chatbot_response("Read this case", user_id=who)[0]
        except Exception as error:
            errors.append(error)

    editor = threading.Thread(target=run, args=("editor",))
    admin = threading.Thread(target=run, args=("admin",))
    editor.start()
    try:
        assert transport["editor_started"].wait(5)
        admin.start()
        admin.join(timeout=10)
        assert not admin.is_alive()
    finally:
        transport["release_editor"].set()
        editor.join(timeout=10)
    assert not editor.is_alive() and not errors
    assert "editor_api_key" in results["editor"] and "admin_api_key" not in results["editor"]
    assert "admin_api_key" in results["admin"] and "editor_api_key" not in results["admin"]
    assert Counter(call[0] for call in transport["calls"]) == Counter({"editor_api_key": 2, "admin_api_key": 2})


def test_real_stdio_tool_timeout_terminates_child(app, identities, monkeypatch):
    from mcp.client import stdio as Stdio

    source = '''
import asyncio
from mcp.server.fastmcp import FastMCP
server = FastMCP("Timeout test")
@server.tool()
async def call_flowintel_api(method: str, path: str, body: dict | None = None) -> str:
    await asyncio.Event().wait()
server.run(transport="stdio")
'''
    parameters = Chatbot.StdioServerParameters
    monkeypatch.setattr(Chatbot, "StdioServerParameters", lambda command, args, env:
                        parameters(command=sys.executable, args=["-c", source], env=env))
    original_create = Stdio._create_platform_compatible_process
    children = []

    async def create_child(*args, **kwargs):
        child = await original_create(*args, **kwargs)
        children.append(child)
        return child

    original_wait = asyncio.wait_for

    async def short_tool_wait(awaitable, timeout):
        return await original_wait(awaitable, timeout=0.02 if timeout == 30 else timeout)

    monkeypatch.setattr(Stdio, "_create_platform_compatible_process", create_child)
    monkeypatch.setattr(Chatbot.asyncio, "wait_for", short_tool_wait)
    with pytest.raises(Exception) as caught:
        invoke(app, identities, "editor")

    def contains_timeout(error):
        return isinstance(error, TimeoutError) or (
            isinstance(error, BaseExceptionGroup) and any(contains_timeout(child) for child in error.exceptions))

    assert contains_timeout(caught.value)
    assert children and all(child.returncode is not None for child in children)
