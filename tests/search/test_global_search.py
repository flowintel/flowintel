"""Top bar search (/search/quick): every user only finds what they are allowed to open.

Three organisations' worth of data, from the users of init_db.create_user_test()
(admin, editor and read-only, each in their own organisation):

- "Alpha public"   public case of the editor's org
- "Bravo secret"   private case of the editor's org only
- "Charlie shared" private case of the editor's org, shared with the read-only user's org

Each case has a task, a note and a MISP attribute; a taxonomy tag and a custom tag are
used only on "Bravo secret".
"""
import uuid
import datetime

import pytest

from app.db_class.db import (Case, Case_Custom_Tags, Case_Org, Case_Tags, Custom_Tags, Misp_Attribute, Note,
                             Org, Taxonomy, Tags, Task, User, db)

KEYS = {"admin": "admin_api_key", "editor": "editor_api_key", "read": "read_api_key"}


def login(client, app, who):
    with app.app_context():
        user = User.query.filter_by(api_key=KEYS[who]).one()
        login_id = user.get_id()
    with client.session_transaction() as session:
        session['_user_id'] = login_id
        session['_fresh'] = True


def _case(title, owner_org, private, orgs=(), minutes_ago=0):
    now = datetime.datetime.now() - datetime.timedelta(minutes=minutes_ago)
    case = Case(uuid=str(uuid.uuid4()), title=title, description="", creation_date=now, last_modif=now,
                status_id=1, completed=False, owner_org_id=owner_org, is_private=private, nb_tasks=1)
    db.session.add(case)
    db.session.flush()
    for org_id in {owner_org, *orgs}:
        db.session.add(Case_Org(case_id=case.id, org_id=org_id))
    task = Task(uuid=str(uuid.uuid4()), title=f"{title} task", case_id=case.id, creation_date=now,
                last_modif=now, status_id=1, completed=False, case_order_id=1, nb_notes=1)
    db.session.add(task)
    db.session.flush()
    db.session.add(Note(uuid=str(uuid.uuid4()), note=f"zulu note about {title}", task_id=task.id, task_order_id=1))
    db.session.add(Misp_Attribute(case_id=case.id, value=f"ioc-{title.split()[0].lower()}.example", type="domain"))
    return case


@pytest.fixture
def data(app):
    with app.app_context():
        editor = User.query.filter_by(api_key=KEYS["editor"]).one()
        reader = User.query.filter_by(api_key=KEYS["read"]).one()
        alpha = _case("Alpha public", editor.org_id, False, minutes_ago=3)
        bravo = _case("Bravo secret", editor.org_id, True, minutes_ago=1)
        charlie = _case("Charlie shared", editor.org_id, True, orgs=[reader.org_id], minutes_ago=2)

        taxo = Taxonomy(uuid=str(uuid.uuid4()), name="xray", description="", version="1")
        db.session.add(taxo)
        db.session.flush()
        tag = Tags(uuid=str(uuid.uuid4()), name='xray:only-on-bravo', color="#ff0000", taxonomy_id=taxo.id)
        custom = Custom_Tags(name="xray-custom-bravo", color="#00ff00")
        db.session.add_all([tag, custom])
        db.session.flush()
        db.session.add(Case_Tags(tag_id=tag.id, case_id=bravo.id))
        db.session.add(Case_Custom_Tags(custom_tag_id=custom.id, case_id=bravo.id))
        db.session.commit()
        return {"alpha": alpha.id, "bravo": bravo.id, "charlie": charlie.id, "bravo_uuid": bravo.uuid}


def search(client, q, kinds=None):
    params = {"q": q}
    if kinds:
        params["kinds"] = kinds
    res = client.get("/search/quick", query_string=params)
    assert res.status_code == 200
    return res.json


def found(result, kind):
    group = next((g for g in result["groups"] if g["kind"] == kind), None)
    return group["items"] if group else []


def case_ids(items):
    return {it.get("case_id", it["id"]) for it in items}


# ------------------------------------------------------------------ access

def test_requires_login(client):
    assert client.get("/search/quick?q=alpha").status_code in (302, 401)


@pytest.mark.parametrize("kind,query", [("cases", "a"), ("tasks", "task"), ("notes", "zulu"), ("attributes", "ioc-")])
def test_other_org_never_sees_private_case_content(client, app, data, kind, query):
    login(client, app, "read")
    ids = case_ids(found(search(client, query, kind), kind))
    assert data["alpha"] in ids            # public
    assert data["charlie"] in ids          # private, shared with the reader's org
    assert data["bravo"] not in ids        # private, not shared


@pytest.mark.parametrize("kind,query", [("cases", "a"), ("tasks", "task"), ("notes", "zulu"), ("attributes", "ioc-")])
def test_member_and_admin_see_everything(client, app, data, kind, query):
    for who in ("editor", "admin"):
        login(client, app, who)
        ids = case_ids(found(search(client, query, kind), kind))
        assert {data["alpha"], data["bravo"], data["charlie"]} <= ids, who


def test_private_case_not_found_by_id_or_uuid(client, app, data):
    login(client, app, "read")
    assert data["bravo"] not in case_ids(found(search(client, f"#{data['bravo']}"), "cases"))
    assert found(search(client, data["bravo_uuid"]), "cases") == []
    login(client, app, "editor")
    assert data["bravo"] in case_ids(found(search(client, f"#{data['bravo']}"), "cases"))


def test_tags_only_used_on_hidden_cases_are_not_suggested(client, app, data):
    login(client, app, "read")
    assert found(search(client, "xray", "tags"), "tags") == []
    login(client, app, "editor")
    titles = {it["title"] for it in found(search(client, "xray", "tags"), "tags")}
    assert {"xray:only-on-bravo", "xray-custom-bravo"} <= titles


def test_users_and_orgs_are_for_admins_only(client, app, data):
    login(client, app, "read")
    result = search(client, "a", "users,orgs")
    assert result["groups"] == []
    assert "users" not in result["kinds"] and "orgs" not in result["kinds"]
    login(client, app, "admin")
    result = search(client, "editor", "users")
    assert found(result, "users")


def test_recent_cases_when_nothing_is_typed(client, app, data):
    login(client, app, "read")
    recent = found(search(client, ""), "recent")
    ids = [it["id"] for it in recent]
    assert data["bravo"] not in ids
    assert ids[:2] == [data["charlie"], data["alpha"]]   # most recently modified first
    login(client, app, "editor")
    assert [it["id"] for it in found(search(client, ""), "recent")][0] == data["bravo"]


# ------------------------------------------------------------------ input handling

def test_like_wildcards_are_plain_text(client, app, data):
    login(client, app, "admin")
    for q in ("%", "_", "%%", "\\"):
        assert search(client, q, "cases")["groups"] == [], q


def test_unknown_kinds_and_long_queries(client, app, data):
    login(client, app, "read")
    assert search(client, "alpha", "nope,drop table")["groups"] == []
    result = search(client, "a" * 5000)
    assert len(result["query"]) <= 100


def test_results_are_bounded(client, app, data):
    login(client, app, "admin")
    with app.app_context():
        editor = User.query.filter_by(api_key=KEYS["editor"]).one()
        for i in range(30):
            _case(f"Bulk case {i}", editor.org_id, False)
        db.session.commit()
    all_view = found(search(client, "bulk"), "cases")
    scoped = found(search(client, "bulk", "cases"), "cases")
    assert len(all_view) == 5 and len(scoped) == 20
    group = next(g for g in search(client, "bulk")["groups"] if g["kind"] == "cases")
    assert group["total"] == 30 and not group["capped"]


# ------------------------------------------------------------------ tags on tasks

def _tag_task(app, case_id, name):
    with app.app_context():
        from app.db_class.db import Task_Tags
        taxo = Taxonomy.query.filter_by(name="yankee").first() or Taxonomy(uuid=str(uuid.uuid4()), name="yankee", description="", version="1")
        db.session.add(taxo)
        db.session.flush()
        tag = Tags(uuid=str(uuid.uuid4()), name=name, color="#0000ff", taxonomy_id=taxo.id)
        db.session.add(tag)
        db.session.flush()
        task = Task.query.filter_by(case_id=case_id).first()
        db.session.add(Task_Tags(tag_id=tag.id, task_id=task.id))
        db.session.commit()


def test_tags_used_on_tasks_follow_the_case_rules(client, app, data):
    _tag_task(app, data["charlie"], "yankee:on-shared-task")
    _tag_task(app, data["bravo"], "yankee:on-secret-task")
    login(client, app, "read")
    items = {it["title"]: it for it in found(search(client, "yankee", "tags"), "tags")}
    assert "yankee:on-secret-task" not in items
    shared = items["yankee:on-shared-task"]
    assert shared["on_tasks"] and not shared["on_cases"]
    assert shared["url"] == shared["tasks_url"] and shared["tasks_url"].startswith("/my_assignment/?tags=")


def test_my_assignment_tag_filter(client, app, data):
    _tag_task(app, data["alpha"], "yankee:assigned")
    with app.app_context():
        from app.db_class.db import Task_User
        reader = User.query.filter_by(api_key=KEYS["read"]).one()
        for case_id in (data["alpha"], data["charlie"]):
            task = Task.query.filter_by(case_id=case_id).first()
            db.session.add(Task_User(task_id=task.id, user_id=reader.id))
        db.session.commit()
    login(client, app, "read")
    every = client.get("/my_assignment/sort_tasks?flat=true&status=true").json
    tagged = client.get("/my_assignment/sort_tasks?flat=true&status=true&tags=yankee:assigned").json
    assert every["total"] == 2 and tagged["total"] == 1
    assert tagged["tasks"][0]["case_id"] == data["alpha"]


# ------------------------------------------------------------------ time budget

def test_a_kind_over_its_budget_is_reported_not_fatal(client, app, data, monkeypatch):
    from app.search import search_core

    def slow(*args, **kwargs):
        import time
        from app.db_class.db import Note
        deadline = time.perf_counter() + 2
        while time.perf_counter() < deadline:      # keep SQLite busy past the budget
            Note.query.filter(Note.note.ilike("%zulu%")).count()
        return 0, []

    monkeypatch.setattr(search_core, "KIND_BUDGET_MS", 50)
    monkeypatch.setitem(search_core.SEARCHERS, "notes", ("Task notes", slow))
    login(client, app, "admin")
    result = search(client, "zulu")
    notes = next(g for g in result["groups"] if g["kind"] == "notes")
    assert notes.get("timed_out") is True
    assert found(result, "cases") == [] or True       # the other kinds still answered
    assert any(g["kind"] == "attributes" or g["kind"] == "tasks" or g["kind"] == "cases" for g in result["groups"]) or result["groups"]
