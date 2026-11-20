"""Completion details of a case (the collapsible panel under "Completion" on the case home).

Everything is counted in SQL: the case page only has the current page of tasks, so the
numbers cannot be computed in the browser.
"""
import datetime

from sqlalchemy import func, case as sql_case

from ..db_class.db import Task, Subtask, Task_User, User, Status
from ..extensions import db

WEEKS = 8


def _week_start(d):
    d = d.date() if isinstance(d, datetime.datetime) else d
    return d - datetime.timedelta(days=d.weekday())


def completion_stats(case_id):
    now = datetime.datetime.now()
    open_filter = db.or_(Task.completed.is_(False), Task.completed.is_(None))

    # tasks per status (open and closed)
    statuses = {s.id: s for s in Status.query.all()}
    by_status = []
    for status_id, completed, nb in (db.session.query(Task.status_id, Task.completed, func.count(Task.id))
                                     .filter(Task.case_id == case_id)
                                     .group_by(Task.status_id, Task.completed).all()):
        s = statuses.get(status_id)
        by_status.append({"id": status_id, "name": s.name if s else "Unknown",
                          "style": s.bootstrap_style if s else "secondary",
                          "order": s.order if s else 999, "completed": bool(completed), "count": nb})
    merged = {}
    for b in by_status:
        m = merged.setdefault(b["id"], {**b, "count": 0})
        m["count"] += b["count"]
    by_status = sorted(merged.values(), key=lambda b: (b["order"] or 0, b["name"]))

    # deadlines of the open tasks
    soon = now + datetime.timedelta(days=7)
    deadlines = db.session.query(
        func.count(sql_case((Task.deadline < now, 1))),
        func.count(sql_case((db.and_(Task.deadline >= now, Task.deadline <= soon), 1))),
        func.count(sql_case((Task.deadline.is_(None), 1))),
    ).filter(Task.case_id == case_id, open_filter).one()

    # open / closed per assignee, and open tasks nobody is assigned to
    per_user = (db.session.query(User.id, User.first_name, User.last_name, User.nickname,
                                 func.count(sql_case((open_filter, 1))),
                                 func.count(sql_case((Task.completed.is_(True), 1))))
                .join(Task_User, Task_User.user_id == User.id)
                .join(Task, Task.id == Task_User.task_id)
                .filter(Task.case_id == case_id)
                .group_by(User.id, User.first_name, User.last_name, User.nickname).all())
    assignees = sorted(({"id": uid, "name": " ".join(x for x in (fn, ln) if x) or nick or f"User #{uid}",
                         "open": o, "closed": c} for uid, fn, ln, nick, o, c in per_user),
                       key=lambda a: (-(a["open"] + a["closed"]), a["name"]))
    unassigned = (Task.query.filter(Task.case_id == case_id, open_filter)
                  .filter(~db.exists().where(Task_User.task_id == Task.id)).count())

    # subtasks
    sub_total, sub_done = db.session.query(
        func.count(Subtask.id), func.count(sql_case((Subtask.completed.is_(True), 1)))
    ).join(Task, Task.id == Subtask.task_id).filter(Task.case_id == case_id).one()

    # tasks created / finished per week, last WEEKS weeks
    first = _week_start(now) - datetime.timedelta(weeks=WEEKS - 1)
    since = datetime.datetime.combine(first, datetime.time.min)
    weeks = [{"week": (first + datetime.timedelta(weeks=i)).isoformat(), "created": 0, "finished": 0} for i in range(WEEKS)]
    index = {w["week"]: w for w in weeks}
    for (d,) in db.session.query(Task.creation_date).filter(Task.case_id == case_id, Task.creation_date >= since):
        w = index.get(_week_start(d).isoformat())
        if w: w["created"] += 1
    for (d,) in db.session.query(Task.finish_date).filter(Task.case_id == case_id, Task.completed.is_(True), Task.finish_date >= since):
        w = index.get(_week_start(d).isoformat())
        if w: w["finished"] += 1

    return {
        "by_status": by_status,
        "overdue": deadlines[0], "due_soon": deadlines[1], "no_deadline": deadlines[2],
        "assignees": assignees[:8], "more_assignees": max(0, len(assignees) - 8), "unassigned": unassigned,
        "subtasks": {"total": sub_total, "done": sub_done},
        "weeks": weeks,
    }
