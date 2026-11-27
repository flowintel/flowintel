"""Compact, paginated candidate lists for the case timeline import dialog."""
from math import ceil

from sqlalchemy import and_, func, or_, select

from ..db_class.db import Case_Misp_Object, Case_Timeline_Event, File, Misp_Attribute, Task, db


PAGE_SIZE = 20
PREVIEW_LENGTH = 160


def _matches(term, *columns):
    return or_(*(column.icontains(term, autoescape=True) for column in columns))


def import_candidates(case, source, term, page, ids_only=False):
    obj, attr = Case_Misp_Object, Misp_Attribute
    if source == "objects":
        query = db.session.query(obj.id, obj.name.label("label")).filter(obj.case_id == case.id)
        if term:
            matching_attributes = select(attr.case_misp_object_id).join(obj).where(
                obj.case_id == case.id, _matches(term, attr.type, attr.object_relation, attr.value)
            )
            query = query.filter(or_(_matches(term, obj.name, obj.uuid), obj.id.in_(matching_attributes)))
        item_id = obj.id
    elif source == "attributes":
        query = db.session.query(
            attr.id, func.substr(attr.value, 1, PREVIEW_LENGTH).label("label"), attr.type.label("detail")
        ).filter(attr.case_id == case.id, attr.case_misp_object_id.is_(None))
        if term:
            query = query.filter(_matches(term, attr.value, attr.type, attr.object_relation))
        item_id = attr.id
    else:
        query = db.session.query(
            File.id, File.name.label("label"), Task.title.label("detail")
        ).outerjoin(Task, and_(Task.id == File.task_id, Task.case_id == case.id)).filter(
            or_(File.case_id == case.id, Task.id.is_not(None))
        )
        if term:
            query = query.filter(_matches(term, File.name, File.file_type, Task.title))
        item_id = File.id

    event = Case_Timeline_Event
    column = event.file_id if source == "files" else event.misp_object_id
    if ids_only:
        # Bulk selection is explicit. Fetch just eligible IDs across matching pages.
        imported = select(column).where(event.case_id == case.id, column.is_not(None))
        source_id = -item_id if source == "attributes" else item_id
        eligible = query.with_entities(item_id).filter(source_id.not_in(imported))
        return {"ids": [value for value, in eligible]}

    offset = (page - 1) * PAGE_SIZE
    rows = query.order_by(item_id.desc()).offset(offset).limit(PAGE_SIZE + 1).all()
    has_next = len(rows) > PAGE_SIZE
    # A nonempty last page (or an empty first page) already gives the exact total.
    if has_next or (offset and not rows):
        total = query.with_entities(func.count(item_id)).scalar()
    else:
        total = offset + len(rows)
    items = [dict(row._mapping) for row in rows[:PAGE_SIZE]]
    ids = [item["id"] for item in items]
    if ids:
        if source == "objects":
            # Pick one representative attribute per visible object. When searching,
            # show a matching value so objects with the same name are distinguishable.
            preview = select(func.min(attr.id)).where(attr.case_misp_object_id.in_(ids))
            if term:
                preview = preview.where(_matches(term, attr.value, attr.type, attr.object_relation))
            details = dict(db.session.query(attr.case_misp_object_id, func.substr(attr.value, 1, PREVIEW_LENGTH))
                           .filter(attr.id.in_(preview.group_by(attr.case_misp_object_id))).all())
            for item in items:
                item["detail"] = details.get(item["id"])

        # The timeline stores standalone attribute IDs as negative MISP object IDs.
        source_ids = [-value for value in ids] if source == "attributes" else ids
        imported = {abs(value) for value, in db.session.query(column).filter(
            event.case_id == case.id, column.in_(source_ids)
        )}
        for item in items:
            item["is_imported"] = item["id"] in imported
            if source == "files":
                item["detail"] = f"Task · {item['detail']}" if item["detail"] else "Case file"

    return {"items": items, "has_next": has_next, "total": total, "total_pages": ceil(total / PAGE_SIZE)}
