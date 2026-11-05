"""Everything dated in a case, for its Calendar panel.

Gathers, in one list of calendar items:
  - the case: creation, deadline, completion, next recurrence
  - its tasks: creation, deadline, completion
  (each with a `period` for the case / task: creation, deadline, completion, time required)
  - files of the case and of its tasks: upload
  - timeline events: the date of the event itself
  - MISP objects and references: creation; MISP attributes: creation, first seen, last seen
  - MISP connectors: sync runs, next scheduled sync, sync conflicts
  - the case history and, for users allowed to read it, the audit log

Each item: {id, kind, title, start, end?, all_day, detail, target, meta, status, body}
`target` tells the page where to go on click: {"tab": ..., "task": id}.
`meta` is a list of [label, value] shown in the preview, `status` {name, style} a
Bootstrap-coloured badge, `body` a longer text (description, note, comment).
"""
import datetime
import re

from ..db_class.db import (
    Task, File, Case_Timeline_Event, Case_Misp_Object, Case_Misp_Object_Reference,
    Misp_Attribute, Connector_Sync_Log, Case_Misp_Sync_Schedule, Case_Misp_Sync_Conflict,
    Status, Task_User, User,
)
from . import common_core as CommonModel

_LOG_LINE = re.compile(r'^\[(.*?)\]\((.*?)\):?\s*(.*)$')


def _iso(value):
    """A stored datetime as ISO text. Stored dates are UTC, the browser shows them in local time."""
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value)
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.isoformat()


def _short(text, length=80):
    text = (text or '').strip().replace('\n', ' ')
    return text if len(text) <= length else text[:length - 1] + '…'


class _Collector:
    def __init__(self):
        self.items = []

    def add(self, kind, uid, title, start, detail='', target=None, end=None, all_day=False,
            meta=None, status=None, body='', label=None, period=None):
        start = _iso(start)
        if not start:
            return
        self.items.append({
            "id": f"{kind}-{uid}",
            "kind": kind,
            "title": title,
            "start": start,
            "end": _iso(end),
            "all_day": all_day,
            "detail": detail or '',
            "target": target or {},
            "meta": [[label, str(value)] for label, value in (meta or []) if value not in (None, '', [])],
            "status": status,
            "body": body or '',
            "label": label,
            "period": period,
        })


def _log_entries(lines, kind, out, local_dates):
    """History and audit lines are "[YYYY-MM-DD HH:MM](user): text", in local server time."""
    for i, line in enumerate(lines or []):
        m = _LOG_LINE.match(line)
        if not m:
            continue
        try:
            date = datetime.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        if local_dates:
            date = date.astimezone()
        # The exact line, so the History tab can scroll to it and outline it
        go = {"tab": "history", "sub": "history-audit" if kind == "audit" else "history-case",
              "entry": {"date": m.group(1), "user": m.group(2), "text": m.group(3)}}
        out.add(kind, i, _short(m.group(3)), date, detail=m.group(2), target=go, body=m.group(3),
                meta=[("By", m.group(2)), ("When", m.group(1))])


def _period(created, deadline, finish, time_required):
    """How long a task or the case runs, for the progress bar of its preview"""
    if not created:
        return None
    return {"start": _iso(created), "deadline": _iso(deadline), "finish": _iso(finish),
            "time_required": time_required or None}


def _fmt(value):
    return f"{value:%Y-%m-%d %H:%M}" if value else None


def get_case_calendar(case, include_logs):
    out = _Collector()
    cid = case.id
    statuses = {st.id: {"name": st.name, "style": st.bootstrap_style} for st in Status.query.all()}

    case_status = statuses.get(case.status_id)
    case_period = _period(case.creation_date, case.deadline, case.finish_date, case.time_required)
    case_meta = [("Created", _fmt(case.creation_date)), ("Deadline", _fmt(case.deadline)),
                 ("Time required", case.time_required), ("Completed", _fmt(case.finish_date)),
                 ("Visibility", "Private" if case.is_private else "Public"), ("Ticket", case.ticket_id)]

    out.add("case", "created", "Case created", case.creation_date, target={"tab": "main"},
            meta=case_meta, status=case_status, period=case_period, body=case.description)
    if case.deadline:
        out.add("deadline", "case", case.title, case.deadline, label="Case deadline",
                detail=case.title + (f" · Time required: {case.time_required}" if case.time_required else ''), target={"tab": "main"},
                meta=case_meta, status=case_status, period=case_period, body=case.description)
    if case.finish_date:
        out.add("case", "finished", "Case completed", case.finish_date, target={"tab": "main"},
                meta=case_meta, status=case_status, period=case_period)
    if case.recurring_date:
        out.add("case", "recurring", "Case recurrence" + (f" ({case.recurring_type})" if case.recurring_type else ''),
                case.recurring_date, target={"tab": "main"}, all_day=True)

    # Tasks
    tasks = Task.query.filter_by(case_id=cid).all()
    task_title = {t.id: t.title for t in tasks}
    user_names = {u.id: f"{u.first_name} {u.last_name}".strip() for u in User.query.all()}
    assignees = {}
    if task_title:
        for tu in Task_User.query.filter(Task_User.task_id.in_(list(task_title))).all():
            assignees.setdefault(tu.task_id, []).append(user_names.get(tu.user_id, f"#{tu.user_id}"))
    for t in tasks:
        go = {"tab": "main", "task": t.id, "completed": bool(t.completed)}
        tk = dict(status=statuses.get(t.status_id), body=t.description,
                  period=_period(t.creation_date, t.deadline, t.finish_date, t.time_required), meta=[
            ("Created", _fmt(t.creation_date)), ("Deadline", _fmt(t.deadline)), ("Time required", t.time_required),
            ("Completed", _fmt(t.finish_date)), ("Assigned to", ", ".join(assignees.get(t.id, [])) or "Nobody"),
            ("Notes", t.notes.count()), ("Files", t.files.count()),
        ])
        # Created and finished the same day: one entry, not the same task twice on that day
        same_day = t.finish_date and t.creation_date and t.finish_date.date() == t.creation_date.date()
        if not same_day:
            out.add("task", f"{t.id}-created", _short(t.title, 70), t.creation_date, target=go, label="Task created", **tk)
        if t.deadline:
            out.add("deadline", f"task-{t.id}", _short(t.title, 70), t.deadline, label="Task deadline",
                    detail=("Finished" if t.completed else "Open") + (f" · Time required: {t.time_required}" if t.time_required else ''),
                    target=go, **tk)
        if t.finish_date:
            out.add("task", f"{t.id}-finished", _short(t.title, 70), t.finish_date, target=go,
                    label="Task created and finished" if same_day else "Task finished", **tk)

    # Files
    task_ids = list(task_title)
    files = File.query.filter((File.case_id == cid) | (File.task_id.in_(task_ids) if task_ids else False)).all()
    for f in files:
        fm = [("Type", f.file_type), ("Size", f"{f.file_size:,} bytes" if f.file_size else None), ("Uploaded", _fmt(f.upload_date)),
              ("Task", task_title.get(f.task_id) if f.task_id else "Case file")]
        if f.task_id:
            out.add("file", f.id, f.name, f.upload_date, label="File of a task",
                    detail=f"Task: {task_title.get(f.task_id, '')}", target={"tab": "main", "task": f.task_id}, meta=fm)
        else:
            out.add("file", f.id, f.name, f.upload_date, label="File of the case", detail="Case file", target={"tab": "files"}, meta=fm)

    # Timeline events
    for ev in Case_Timeline_Event.query.filter_by(case_id=cid).all():
        out.add("timeline", ev.id, _short(ev.description), ev.date_parsed,
                detail=_short(ev.additional_note, 200), target={"tab": "timeline"}, body=ev.additional_note,
                meta=[("Date", ev.date_text), ("Source", "MISP object" if (ev.misp_object_id or 0) > 0 else
                      "MISP attribute" if (ev.misp_object_id or 0) < 0 else "File" if ev.file_id else "Added by hand")])

    # MISP
    objects = Case_Misp_Object.query.filter_by(case_id=cid).all()
    object_name = {o.id: o.name for o in objects}
    for o in objects:
        out.add("misp", f"object-{o.id}", f"MISP object: {o.name}", o.creation_date, target={"tab": "misp"},
                meta=[("Template", o.name), ("UUID", o.uuid), ("Attributes", Misp_Attribute.query.filter_by(case_misp_object_id=o.id).count()),
                      ("Created", _fmt(o.creation_date))])
    for r in Case_Misp_Object_Reference.query.filter_by(case_id=cid).all():
        out.add("misp", f"ref-{r.id}", f"MISP reference: {r.relationship_type or 'relationship'}",
                r.creation_date, detail=_short(r.comment, 200), target={"tab": "misp"})
    for a in Misp_Attribute.query.filter_by(case_id=cid).all():
        where = f"Object: {object_name.get(a.case_misp_object_id, '')}" if a.case_misp_object_id else "Standalone attribute"
        label = f"{a.type} {_short(a.value, 50)}"
        am = [("Type", a.type), ("Value", a.value), ("Relation", a.object_relation), ("In", where),
              ("IDS", "Yes" if a.ids_flag else "No"), ("First seen", _fmt(a.first_seen)), ("Last seen", _fmt(a.last_seen))]
        out.add("misp", f"attr-{a.id}", f"MISP attribute: {label}", a.creation_date, detail=where, target={"tab": "misp"},
                meta=am, body=a.comment)
        if a.first_seen:
            out.add("seen", f"first-{a.id}", f"First seen: {label}", a.first_seen, detail=where, target={"tab": "misp"}, meta=am, body=a.comment)
        if a.last_seen:
            out.add("seen", f"last-{a.id}", f"Last seen: {label}", a.last_seen, detail=where, target={"tab": "misp"}, meta=am, body=a.comment)

    for log in Connector_Sync_Log.query.filter_by(case_id=cid).all():
        out.add("sync", f"log-{log.id}", f"MISP sync {log.direction or ''}: {log.status or ''}".strip(), log.timestamp,
                detail=_short(log.message, 200), target={"tab": "misp"}, body=log.message,
                meta=[("Direction", log.direction), ("Result", log.status), ("Synced", log.objects_synced), ("Failed", log.objects_failed)])
    for sch in Case_Misp_Sync_Schedule.query.filter_by(case_id=cid, enabled=True).all():
        if sch.next_run_at:
            out.add("sync", f"next-{sch.id}", f"Next MISP {sch.direction or 'sync'} ({sch.interval})", sch.next_run_at,
                    target={"tab": "misp"})
    for c in Case_Misp_Sync_Conflict.query.filter_by(case_id=cid).all():
        out.add("sync", f"conflict-{c.id}", f"MISP conflict on {c.item_type or 'item'} ({c.status})", c.created_at,
                target={"tab": "misp"})

    # History and audit
    if include_logs:
        _log_entries(CommonModel.get_history(case.uuid), "history", out, local_dates=True)
        _log_entries(CommonModel.get_audit_logs(cid), "audit", out, local_dates=True)

    return out.items
