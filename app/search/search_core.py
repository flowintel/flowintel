"""Global search (top bar): one bounded query per kind of object, with the user's rights
applied in SQL so it stays fast and safe on large instances.

Visibility follows the case rules used everywhere else: an admin sees everything; anyone
else sees public cases and the private cases their organisation takes part in. Tasks,
notes and MISP attributes inherit the visibility of their case. Users and organisations
are only searched for admins.

Every query is limited (`limit` rows + 1 to know if there is more) and its total is
counted on a capped subquery (COUNT_CAP), so a frequent word never scans/returns
thousands of rows.
"""
import re
import time
from contextlib import contextmanager

from sqlalchemy.exc import DBAPIError

from sqlalchemy import and_, case as sa_case, desc, exists, func, literal, or_, select, true

from ..db_class.db import (Case, Case_Custom_Tags, Case_Galaxy_Tags, Case_Misp_Object, Case_Org, Case_Tags,
                           Case_Template, Cluster, Custom_Tags, Misp_Attribute, Note, Note_Template_Model, Org,
                           Tags, Task, Task_Custom_Tags, Task_Galaxy_Tags, Task_Tags, Task_Template, User)
from ..extensions import db

COUNT_CAP = 100          # totals above this are shown as "100+"
TAG_CANDIDATES = 40     # tags / clusters looked at by name before checking where they are used
KIND_BUDGET_MS = 2500    # time a kind may take (all its queries) before it is given up
MIN_LEN_BIG_TEXT = 3     # notes / attributes: no 1-2 character search (it matches everything)
MAX_QUERY_LEN = 100
DEFAULT_LIMIT = 5        # rows per kind in the "all" view
SCOPED_LIMIT = 20        # rows when a single kind is asked
SNIPPET = 120            # characters of context around a match in a note / description

KINDS = ("cases", "tasks", "notes", "attributes", "tags", "templates", "users", "orgs")
ADMIN_KINDS = {"users", "orgs"}


def _like(text):
    """ILIKE pattern for a substring, with the LIKE wildcards of the user's text escaped."""
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def _ilike(column, text):
    return column.ilike(_like(text), escape="\\")


def _starts_first(column, text):
    """ORDER BY key: values starting with the text first."""
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return sa_case((func.lower(column).like(esc.lower() + "%", escape="\\"), 0), else_=1)


def visible_case_clause(user):
    """SQL condition on Case for what `user` may see (case/common_core.visible_case_filter)."""
    from ..case.common_core import visible_case_filter
    return visible_case_filter(user)


def _page(query, limit):
    """(rows, total) — rows limited, total counted up to COUNT_CAP + 1."""
    rows = query.limit(limit).all()
    if len(rows) < limit:
        return rows, len(rows)
    capped = query.order_by(None).limit(COUNT_CAP + 1).subquery()
    total = db.session.query(func.count()).select_from(capped).scalar()
    return rows, total


def _snippet(text, needle):
    """A short extract of `text` around the first match of `needle` (plain text)."""
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text).strip()
    i = flat.lower().find(needle.lower())
    if i < 0:
        return flat[:SNIPPET] + ("…" if len(flat) > SNIPPET else "")
    start = max(0, i - SNIPPET // 3)
    end = min(len(flat), start + SNIPPET)
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


def _fmt(d):
    return d.strftime("%Y-%m-%d %H:%M") if d else None


# ---------------------------------------------------------------- one function per kind

def _case_item(c):
    return {
        "id": c.id, "title": c.title, "url": f"/case/{c.id}",
        "sub": c.ticket_id or "", "status_id": c.status_id, "completed": bool(c.completed),
        "is_private": bool(c.is_private), "privileged": bool(c.privileged_case),
        "deadline": _fmt(c.deadline), "last_modif": _fmt(c.last_modif),
    }


def recent_cases(user, limit=6):
    """Open cases the user can see, most recently modified first (search opened, nothing typed)."""
    rows = Case.query.filter(Case.completed.is_not(True), visible_case_clause(user))\
        .order_by(desc(Case.last_modif), desc(Case.id)).limit(limit).all()
    return [_case_item(c) for c in rows]


def _exact_first(model, number, user, extra_filter=None):
    """The row whose id is `number` ("#123"), if the user may see it: one primary-key lookup."""
    if number is None:
        return None
    query = model.query.filter(model.id == number)
    if model is Task:
        query = query.join(Case, Case.id == Task.case_id)
    return query.filter(visible_case_clause(user)).first()


# Big tables (cases, tasks, notes, attributes) are only ordered on indexed columns, so the
# database can walk the index and stop after `limit` matches instead of sorting them all.

def _cases(text, user, limit, number):
    conds = [_ilike(Case.title, text), _ilike(Case.ticket_id, text), Case.uuid == text]
    query = Case.query.filter(or_(*conds), visible_case_clause(user)).order_by(desc(Case.last_modif), desc(Case.id))
    rows, total = _page(query, limit)
    exact = _exact_first(Case, number, user)
    if exact:
        rows = [exact] + [c for c in rows if c.id != exact.id][:limit - 1]
        total = max(total, len(rows))
    return total, [_case_item(c) for c in rows]


def _tasks(text, user, limit, number):
    conds = [_ilike(Task.title, text), Task.uuid == text]
    query = db.session.query(Task, Case.title).join(Case, Case.id == Task.case_id).filter(
        or_(*conds), visible_case_clause(user)
    ).order_by(desc(Task.last_modif), desc(Task.id))
    rows, total = _page(query, limit)
    exact = _exact_first(Task, number, user)
    if exact:
        rows = [(exact, db.session.get(Case, exact.case_id).title)] + [r for r in rows if r[0].id != exact.id][:limit - 1]
        total = max(total, len(rows))
    return total, [{
        "id": t.id, "title": t.title, "url": f"/case/{t.case_id}?task={t.id}#task-{t.id}",
        "case_id": t.case_id, "case_title": case_title, "status_id": t.status_id,
        "completed": bool(t.completed), "deadline": _fmt(t.deadline),
    } for t, case_title in rows]


def _notes(text, user, limit, number):
    if len(text) < MIN_LEN_BIG_TEXT:
        return 0, []
    query = db.session.query(Note.id, Note.note, Task.id, Task.title, Case.id, Case.title)\
        .join(Task, Task.id == Note.task_id).join(Case, Case.id == Task.case_id)\
        .filter(_ilike(Note.note, text), visible_case_clause(user))\
        .order_by(desc(Note.id))
    rows, total = _page(query, limit)
    return total, [{
        "id": nid, "title": task_title, "url": f"/case/{case_id}?task={task_id}#task-{task_id}",
        "snippet": _snippet(note, text), "case_id": case_id, "case_title": case_title,
    } for nid, note, task_id, task_title, case_id, case_title in rows]


def _attributes(text, user, limit, number):
    if len(text) < MIN_LEN_BIG_TEXT:
        return 0, []
    case_id = func.coalesce(Misp_Attribute.case_id, Case_Misp_Object.case_id)
    query = db.session.query(Misp_Attribute.id, Misp_Attribute.value, Misp_Attribute.type,
                             Case_Misp_Object.name, Case.id, Case.title)\
        .outerjoin(Case_Misp_Object, Case_Misp_Object.id == Misp_Attribute.case_misp_object_id)\
        .join(Case, Case.id == case_id)\
        .filter(_ilike(Misp_Attribute.value, text), visible_case_clause(user))\
        .order_by(desc(Misp_Attribute.id))
    rows, total = _page(query, limit)
    return total, [{
        "id": aid, "title": value, "type": a_type, "object": obj_name or "",
        "url": f"/case/{cid}?tab=misp", "case_id": cid, "case_title": case_title,
    } for aid, value, a_type, obj_name, cid, case_title in rows]


def _tags(text, user, limit, number):
    """Taxonomy tags, custom tags and galaxy clusters used on a case or a task the user can
    see (one only on someone else's private case is never suggested: it would reveal it).
    Each item says where it is used and links to the case list and to My assignments,
    both filtered on it."""
    from urllib.parse import quote
    # (model, case link table + columns, task link table + columns, kind, name columns, url param, value)
    specs = (
        (Tags, Case_Tags, Case_Tags.tag_id, Case_Tags.case_id, Task_Tags, Task_Tags.tag_id, Task_Tags.task_id,
         "taxonomy", (Tags.name,), "tags", lambda t: t.name),
        (Custom_Tags, Case_Custom_Tags, Case_Custom_Tags.custom_tag_id, Case_Custom_Tags.case_id,
         Task_Custom_Tags, Task_Custom_Tags.custom_tag_id, Task_Custom_Tags.task_id,
         "custom", (Custom_Tags.name,), "tags", lambda t: t.name),
        (Cluster, Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id, Case_Galaxy_Tags.case_id,
         Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id, Task_Galaxy_Tags.task_id,
         "cluster", (Cluster.name, Cluster.tag), "clusters", lambda c: c.tag),
    )
    # Two steps, so a tag used a million times costs no more than one used once:
    # 1. a few candidates by name (catalog tables, small); 2. for each, one indexed lookup
    # "used on a visible case / task?" that stops at the first row found.
    is_admin = user.is_admin()
    visible = visible_case_clause(user)

    def used(link_tbl, ref_col, obj_col, obj_id, via_task):
        q = db.session.query(literal(1)).select_from(link_tbl).filter(ref_col == obj_id)
        if not is_admin:
            if via_task:
                q = q.join(Task, Task.id == obj_col).join(Case, Case.id == Task.case_id)
            else:
                q = q.join(Case, Case.id == obj_col)
            q = q.filter(visible)
        return q.limit(1).first() is not None

    items, more = [], False
    for model, c_tbl, c_ref, c_obj, t_tbl, t_ref, t_obj, kind, cols, param, value in specs:
        candidates = model.query.filter(or_(*[_ilike(c, text) for c in cols]))\
            .order_by(_starts_first(cols[0], text), cols[0]).limit(TAG_CANDIDATES + 1).all()
        more = more or len(candidates) > TAG_CANDIDATES
        found_here = 0
        for obj in candidates[:TAG_CANDIDATES]:
            if found_here >= limit:
                more = True
                break
            on_case = used(c_tbl, c_ref, c_obj, obj.id, False)
            on_task = used(t_tbl, t_ref, t_obj, obj.id, True)
            if not (on_case or on_task):
                continue
            found_here += 1
            val = quote(value(obj))
            item = {"id": kind[0] + str(obj.id), "kind": kind, "title": value(obj),
                    "color": getattr(obj, "color", None), "icon": getattr(obj, "icon", None),
                    "description": getattr(obj, "description", "") or "",
                    "on_cases": on_case, "on_tasks": on_task,
                    "cases_url": f"/case/?{param}={val}", "tasks_url": f"/my_assignment/?{param}={val}"}
            item["url"] = item["cases_url"] if on_case else item["tasks_url"]
            items.append(item)
    total = len(items) + (COUNT_CAP + 1 if more else 0)
    return min(total, COUNT_CAP + 1), items[:limit]


def _templates(text, user, limit, number):
    items, total = [], 0
    for model, kind, url in ((Case_Template, "case", "/templating/case/{}"),
                             (Task_Template, "task", "/templating/tasks"),
                             (Note_Template_Model, "note", "/tools/note_template_view/{}")):
        query = model.query.filter(_ilike(model.title, text)).order_by(_starts_first(model.title, text), model.title)
        rows, n = _page(query, limit)
        total += n
        items += [{"id": f"{kind}{t.id}", "kind": kind, "title": t.title,
                   "url": url.format(t.id)} for t in rows]
    return min(total, COUNT_CAP + 1), items[:limit]


def _users(text, user, limit, number):
    full = func.lower(func.coalesce(User.first_name, "") + " " + func.coalesce(User.last_name, ""))
    query = db.session.query(User, Org.name).outerjoin(Org, Org.id == User.org_id).filter(
        or_(_ilike(User.first_name, text), _ilike(User.last_name, text), _ilike(User.email, text),
            _ilike(User.nickname, text), full.like(_like(text.lower()), escape="\\"))
    ).order_by(User.first_name, User.last_name)
    rows, total = _page(query, limit)
    return total, [{
        "id": u.id, "title": f"{u.first_name} {u.last_name}".strip(), "sub": u.email,
        "org": org_name or "", "url": "/admin/users?q=" + (u.email or ""),
        "user": {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "nickname": u.nickname},
    } for u, org_name in rows]


def _orgs(text, user, limit, number):
    query = Org.query.filter(_ilike(Org.name, text)).order_by(_starts_first(Org.name, text), Org.name)
    rows, total = _page(query, limit)
    return total, [{"id": o.id, "title": o.name, "sub": (o.description or "")[:80], "url": "/admin/orgs"} for o in rows]


@contextmanager
def _time_budget(ms):
    """Abort the queries of one kind after `ms`: statement timeout on PostgreSQL / MySQL /
    MariaDB, progress handler on SQLite. Raises DBAPIError when the budget is exceeded."""
    conn = db.session.connection()
    dialect = conn.dialect.name
    raw = None
    if dialect == "postgresql":
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {int(ms)}")
    elif dialect == "mysql":
        conn.exec_driver_sql(f"SET SESSION max_execution_time = {int(ms)}")
    elif dialect == "mariadb":
        conn.exec_driver_sql(f"SET SESSION max_statement_time = {ms / 1000:.3f}")
    elif dialect == "sqlite":
        raw = conn.connection.driver_connection
        deadline = time.perf_counter() + ms / 1000
        raw.set_progress_handler(lambda: 1 if time.perf_counter() > deadline else 0, 20000)
    try:
        yield
    finally:
        if raw is not None:
            raw.set_progress_handler(None, 0)
        elif dialect == "mysql":
            conn.exec_driver_sql("SET SESSION max_execution_time = 0")
        elif dialect == "mariadb":
            conn.exec_driver_sql("SET SESSION max_statement_time = 0")


SEARCHERS = {
    "cases": ("Cases", _cases), "tasks": ("Tasks", _tasks), "notes": ("Task notes", _notes),
    "attributes": ("MISP attributes", _attributes), "tags": ("Tags & galaxies", _tags),
    "templates": ("Templates", _templates), "users": ("Users", _users), "orgs": ("Organisations", _orgs),
}


def allowed_kinds(user):
    return [k for k in KINDS if k not in ADMIN_KINDS or user.is_admin()]


def quick_search(text, user, kinds=None):
    """{"query", "groups": [{"kind", "label", "total", "capped", "items"}], "took_ms"}"""
    started = time.perf_counter()
    text = (text or "").strip()[:MAX_QUERY_LEN]
    allowed = allowed_kinds(user)
    kinds = [k for k in (kinds or allowed) if k in allowed]
    groups = []
    # "123": also an exact id match on cases / tasks. "#123" is an id only: one primary-key
    # lookup per kind instead of scanning every title for the digits.
    number = int(text.lstrip("#")) if text.lstrip("#").isdigit() else None
    needle = text.lstrip("#") if number is not None else text
    if text.startswith("#") and number is not None:
        id_only = {"cases": Case, "tasks": Task}
        for kind in [k for k in kinds if k in id_only]:
            obj = _exact_first(id_only[kind], number, user)
            if obj:
                item = _case_item(obj) if kind == "cases" else {
                    "id": obj.id, "title": obj.title, "url": f"/case/{obj.case_id}?task={obj.id}#task-{obj.id}",
                    "case_id": obj.case_id, "case_title": db.session.get(Case, obj.case_id).title,
                    "status_id": obj.status_id, "completed": bool(obj.completed), "deadline": _fmt(obj.deadline)}
                groups.append({"kind": kind, "label": SEARCHERS[kind][0], "total": 1, "capped": False, "items": [item]})
        return {"query": text, "groups": groups, "kinds": allowed,
                "took_ms": round((time.perf_counter() - started) * 1000)}
    if not needle and (not kinds or kinds == ["cases"] or set(kinds) == set(allowed)):
        items = recent_cases(user)
        if items:
            groups.append({"kind": "recent", "label": "Recent cases", "total": len(items), "capped": False, "items": items})
    elif needle:
        limit = SCOPED_LIMIT if len(kinds) == 1 else DEFAULT_LIMIT
        for kind in kinds:
            label, searcher = SEARCHERS[kind]
            try:
                with _time_budget(KIND_BUDGET_MS):
                    total, items = searcher(needle, user, limit, number)
            except DBAPIError:
                # too slow for this kind (huge table, very common word): say so, keep the rest
                db.session.rollback()
                groups.append({"kind": kind, "label": label, "total": 0, "capped": False, "items": [], "timed_out": True})
                continue
            if items:
                groups.append({"kind": kind, "label": label, "total": min(total, COUNT_CAP),
                               "capped": total > COUNT_CAP, "items": items})
    return {"query": text, "groups": groups, "kinds": allowed,
            "took_ms": round((time.perf_counter() - started) * 1000)}
