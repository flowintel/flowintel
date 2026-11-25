"""Candidates for "link a case" (the case picker of the linked cases modal).

- "#123" / "123": that case first;
- otherwise title, ticket id or UUID, open cases before finished ones;
- nothing typed: suggestions — cases sharing tags / galaxy clusters with this case, then the
  cases the user modified last.
The case itself and the cases already linked are never offered; only visible cases are.
"""
import re

from sqlalchemy import desc, func, or_, case as sa_case

from ..db_class.db import Case, Case_Tags, Case_Galaxy_Tags, Case_Link_Case, Org
from ..extensions import db
from ..search.search_core import _ilike, visible_case_clause, _fmt

LIMIT = 12


def _taken_ids(case_id):
    rows = db.session.query(Case_Link_Case.case_id_1, Case_Link_Case.case_id_2)\
        .filter(or_(Case_Link_Case.case_id_1 == case_id, Case_Link_Case.case_id_2 == case_id)).all()
    return {case_id} | {a for a, _ in rows} | {b for _, b in rows}


def _item(c, orgs, reason=""):
    return {
        "id": c.id, "title": c.title, "ticket_id": c.ticket_id or "", "status_id": c.status_id,
        "completed": bool(c.completed), "is_private": bool(c.is_private), "privileged": bool(c.privileged_case),
        "owner_org": orgs.get(c.owner_org_id), "deadline": _fmt(c.deadline), "last_modif": _fmt(c.last_modif),
        "reason": reason,
    }


def _org_names(cases):
    ids = {c.owner_org_id for c in cases if c.owner_org_id}
    return dict(db.session.query(Org.id, Org.name).filter(Org.id.in_(ids)).all()) if ids else {}


def link_candidates(case_id, user, text=""):
    text = (text or "").strip()
    taken = _taken_ids(case_id)
    base = Case.query.filter(visible_case_clause(user), Case.id.notin_(taken))

    if not text:
        # cases sharing the most tags / clusters with this one
        shared = db.session.query(Case_Tags.case_id.label("cid"))\
            .filter(Case_Tags.tag_id.in_(db.session.query(Case_Tags.tag_id).filter(Case_Tags.case_id == case_id)))\
            .union_all(db.session.query(Case_Galaxy_Tags.case_id.label("cid"))
                       .filter(Case_Galaxy_Tags.cluster_id.in_(
                           db.session.query(Case_Galaxy_Tags.cluster_id).filter(Case_Galaxy_Tags.case_id == case_id)))).subquery()
        common = db.session.query(shared.c.cid, func.count().label("n")).group_by(shared.c.cid).subquery()
        similar = base.join(common, common.c.cid == Case.id).filter(Case.completed.is_not(True))\
            .add_columns(common.c.n).order_by(desc(common.c.n), desc(Case.last_modif)).limit(5).all()
        recent = base.filter(Case.completed.is_not(True), Case.id.notin_([c.id for c, _ in similar]))\
            .order_by(desc(Case.last_modif), desc(Case.id)).limit(LIMIT - len(similar)).all()
        orgs = _org_names([c for c, _ in similar] + recent)
        return {
            "suggested": [_item(c, orgs, f"{n} tag{'s' if n > 1 else ''} in common") for c, n in similar],
            "recent": [_item(c, orgs, "recently modified") for c in recent],
        }

    m = re.fullmatch(r"#?(\d+)", text)
    number = int(m.group(1)) if m else None
    conds = [_ilike(Case.title, text), _ilike(Case.ticket_id, text), Case.uuid == text]
    if number is not None:
        conds.append(Case.id == number)
    rows = base.filter(or_(*conds))\
        .order_by(sa_case((Case.id == (number if number is not None else -1), 0), else_=1),
                  sa_case((Case.completed.is_(True), 1), else_=0),
                  desc(Case.last_modif), desc(Case.id)).limit(LIMIT).all()
    orgs = _org_names(rows)
    return {"results": [_item(c, orgs) for c in rows]}
