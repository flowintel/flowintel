"""Data for the MISP column browser (static/js/misp-index-filter-browser.js).

Same JSON as MISP's `IndexPicker` (tags/pickerScopes, tags/pickerSearch,
tags/pickerTree, galaxies/pickerScopes, galaxy_clusters/pickerSearch), built
from Flowintel's taxonomies, tags, galaxies and clusters, so the browser runs
unchanged.
"""
import re

from sqlalchemy import func

from ..db_class.db import Taxonomy, Tags, Galaxy, Cluster, Custom_Tags

LIMIT = 20
MAX_LIMIT = 200
MIN_TERM = 2
CONTAINS_FROM = 3
DESCRIPTION_LENGTH = 160

# The galaxy namespaces the browser groups by (MISP keeps one per galaxy;
# Flowintel does not store it, so it comes from the galaxy type).
_GALAXY_NAMESPACES = ("mitre", "tidal", "disarm", "nist-nice")


class Usage:
    """For a filter: only what is set on at least one object of a scope
    (case, task, case_template, task_template), as tag_filter.js offered it.
    None everywhere below = everything (the editor)."""
    LINKS = {
        "case": ("Case_Tags", "Case_Galaxy_Tags", "Case_Custom_Tags"),
        "task": ("Task_Tags", "Task_Galaxy_Tags", "Task_Custom_Tags"),
        "case_template": ("Case_Template_Tags", "Case_Template_Galaxy_Tags", "Case_Template_Custom_Tags"),
        "task_template": ("Task_Template_Tags", "Task_Template_Galaxy_Tags", "Task_Template_Custom_Tags"),
    }

    def __init__(self, scope, user, case_id=None):
        import importlib
        models = importlib.import_module("app.db_class.db")
        from .common_core import _classification_usage_ids
        tags, galaxies, custom = (getattr(models, n) for n in self.LINKS[scope])
        cid = case_id if scope == "task" else None
        self.tag_ids = _classification_usage_ids(tags, tags.tag_id, user, cid)
        self.cluster_ids = _classification_usage_ids(galaxies, galaxies.cluster_id, user, cid)
        self.custom_ids = _classification_usage_ids(custom, custom.custom_tag_id, user, cid)


def limit_of(value):
    try:
        return max(1, min(MAX_LIMIT, int(value)))
    except (TypeError, ValueError):
        return LIMIT


def _like(term):
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search(query, column, term, to_row, limit, min_term=MIN_TERM):
    """Prefix matches first, then (from 3 characters) matches anywhere."""
    term = (term or "").strip().lower()
    if len(term) < min_term:
        return []
    found = {}

    def collect(rows):
        for r in rows:
            out = to_row(r)
            if out is not None and out["value"] not in found and len(found) < limit:
                found[out["value"]] = out

    if term == "":
        collect(query.limit(limit).all())
        return list(found.values())
    like = _like(term)
    collect(query.filter(func.lower(column).like(like + "%", escape="\\")).limit(limit).all())
    if len(found) < limit and len(term) >= CONTAINS_FROM:
        collect(query.filter(func.lower(column).like("%" + like + "%", escape="\\")).limit(limit).all())
    return list(found.values())


def tag_parts(name):
    """`ns:predicate` or `ns:predicate="value"`, lowercased."""
    i = name.find(":")
    if i <= 0:
        return None
    rest = name[i + 1:]
    value = None
    m = re.match(r'^(.+?)="(.*)"$', rest, re.S)
    if m:
        rest, value = m.group(1), m.group(2).lower()
    return {"namespace": name[:i].lower(), "predicate": rest.lower(), "value": value}


def _shorten(text):
    if not text:
        return None
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
    return text if len(text) <= DESCRIPTION_LENGTH else text[:DESCRIPTION_LENGTH - 1].rstrip() + "…"


def _tags_query():
    return Tags.query.join(Taxonomy, Taxonomy.id == Tags.taxonomy_id)\
        .filter(Tags.exclude == False, Taxonomy.exclude == False)  # noqa: E712


def tag_row(tag):
    return {
        "value": tag.name,
        "label": tag.name,
        "style": {"colour": tag.color or None},
        "id": tag.id,
    }


##########
#  Tags  #
##########

def tag_scopes(usage=None):
    tq = _tags_query()
    if usage:
        tq = tq.filter(Tags.id.in_(usage.tag_ids))
    counts = dict(
        tq.with_entities(Tags.taxonomy_id, func.count(Tags.id)).group_by(Tags.taxonomy_id).all()
    )
    taxonomies = []
    for t in Taxonomy.query.filter_by(exclude=False).order_by(Taxonomy.name).all():
        if usage and not counts.get(t.id):
            continue
        taxonomies.append({
            "namespace": t.name,
            "description": t.description,
            "enabled": True,
            "exclusive": False,
            "tags": counts.get(t.id, 0),
            "pinned": None,
            "preferred": None,
        })
    # MISP's "No namespace" scope holds Flowintel's custom tags (the browser
    # strings rename it "Custom tags"): tags with no "namespace:" prefix.
    cq = Custom_Tags.query.filter_by(is_active=True)
    if usage:
        cq = cq.filter(Custom_Tags.id.in_(usage.custom_ids))
    no_namespace = cq.count()
    return {"taxonomies": taxonomies, "namespaces": [], "no_namespace": no_namespace}


def custom_tag_row(tag):
    row = {
        "value": tag.name,
        "label": tag.name,
        "style": {"colour": tag.color or None},
        "id": tag.id,
        "custom": True,
    }
    if tag.icon:
        row["icon"] = tag.icon
    return row


def search_custom_tags(term, limit, min_term, usage=None):
    query = Custom_Tags.query.filter_by(is_active=True).order_by(Custom_Tags.name)
    if usage:
        query = query.filter(Custom_Tags.id.in_(usage.custom_ids))
    return _search(query, Custom_Tags.name, term, custom_tag_row, limit, min_term)


def search_tags(term, scope=None, predicate=None, limit=None, usage=None):
    query = _tags_query()
    if usage:
        query = query.filter(Tags.id.in_(usage.tag_ids))
    scope = (scope or "").strip()
    limit = limit_of(limit)
    if scope == "-":
        return search_custom_tags(term, limit, 0, usage)
    if scope:
        if scope == "-":
            query = query.filter(~Tags.name.like("_%:%"))
        else:
            head = _like(scope.lower()) + ":"
            predicate = (predicate or "").strip()
            if not predicate:
                query = query.filter(func.lower(Tags.name).like(head + "%", escape="\\"))
            else:
                query = query.filter(
                    (func.lower(Tags.name) == (scope + ":" + predicate).lower())
                    | func.lower(Tags.name).like(head + _like(predicate.lower()) + "=%", escape="\\")
                )
    query = query.order_by(Tags.name)
    rows = _with_taxonomy(_search(query, Tags.name, term, tag_row, limit, 0 if scope else MIN_TERM))
    if not scope and len(rows) < limit:
        rows += search_custom_tags(term, limit - len(rows), MIN_TERM, usage)
    return rows


def _with_taxonomy(rows):
    """What the taxonomy says about each tag: Flowintel keeps it on the tag itself."""
    if not rows:
        return rows
    by_name = {t.name: t for t in Tags.query.filter(Tags.name.in_([r["value"] for r in rows])).all()}
    for row in rows:
        parts = tag_parts(row["value"])
        tag = by_name.get(row["value"])
        if parts is None or tag is None:
            continue
        expanded = tag.description or parts["value"] or parts["predicate"]
        row["taxonomy"] = {
            "namespace": tag.name.split(":", 1)[0],
            "predicate": parts["predicate"],
            "predicate_expanded": parts["predicate"],
            "entry": parts["value"],
            "expanded": expanded,
            "numerical_value": None,
        }
    return rows


def taxonomy_tree(namespace, usage=None):
    taxonomy = Taxonomy.query.filter(
        func.lower(Taxonomy.name) == (namespace or "").strip().lower(),
        Taxonomy.exclude == False,  # noqa: E712
    ).first()
    if taxonomy is None:
        return None
    ns = taxonomy.name
    predicates = {}
    order = []
    tq = Tags.query.filter_by(taxonomy_id=taxonomy.id, exclude=False)
    if usage:
        tq = tq.filter(Tags.id.in_(usage.tag_ids))
    for tag in tq.order_by(Tags.id).all():
        rest = tag.name[len(ns) + 1:] if tag.name.lower().startswith(ns.lower() + ":") else tag.name
        m = re.match(r'^(.+?)="(.*)"$', rest, re.S)
        pv, value = (m.group(1), m.group(2)) if m else (rest, None)
        if pv not in predicates:
            predicates[pv] = {
                "value": pv, "expanded": None, "description": None, "colour": None, "exclusive": False,
                "tag": None, "tag_exists": None, "tag_id": None, "local_only": False, "entries": [],
            }
            order.append(pv)
        p = predicates[pv]
        if value is None:
            p.update({
                "expanded": tag.description, "colour": tag.color or None,
                "tag": tag.name, "tag_exists": True, "tag_id": tag.id,
            })
        else:
            p["entries"].append({
                "value": value, "expanded": tag.description, "description": None,
                "colour": tag.color or None, "numerical_value": None,
                "tag": tag.name, "tag_exists": True, "tag_id": tag.id, "local_only": False,
            })
    out = []
    for pv in order:
        p = predicates[pv]
        if p["entries"]:
            # A predicate with entries is a heading, never a tag of its own (as in MISP).
            if p["tag"]:
                p["entries"].insert(0, {
                    "value": pv, "expanded": p["expanded"], "description": None, "colour": p["colour"],
                    "numerical_value": None, "tag": p["tag"], "tag_exists": True, "tag_id": p["tag_id"],
                    "local_only": False,
                })
            p.update({"tag": None, "tag_exists": None, "tag_id": None})
        out.append(p)
    return {"namespace": ns, "description": taxonomy.description, "exclusive": False, "predicates": out}


##############
#  Galaxies  #
##############

def icon_class(icon):
    if not icon or not re.match(r"^[a-z0-9-]+$", icon):
        return None
    return "fas fa-" + icon


def galaxy_namespace(galaxy):
    t = (galaxy.type or "").lower()
    for ns in _GALAXY_NAMESPACES:
        if t.startswith(ns + "-") or t == ns:
            return ns
    return "misp"


def galaxy_scopes(usage=None):
    cq = Cluster.query.filter_by(exclude=False)
    if usage:
        cq = cq.filter(Cluster.id.in_(usage.cluster_ids))
    counts = dict(
        cq
        .with_entities(Cluster.galaxy_id, func.count(func.distinct(Cluster.tag)))
        .group_by(Cluster.galaxy_id).all()
    )
    out = []
    for g in Galaxy.query.filter_by(exclude=False).order_by(Galaxy.name).all():
        if not counts.get(g.id):
            continue
        out.append({
            "type": g.type,
            "name": g.name,
            "namespace": galaxy_namespace(g),
            "icon": icon_class(g.icon),
            "description": g.description,
            "clusters": counts[g.id],
            "in_use": 0,
            "kill_chain": None,
            "kill_chain_order": None,
            "preferred": None,
            "pinned": None,
            "default": True,
        })
    return out


def cluster_row(cluster, galaxy):
    return {
        "value": cluster.tag,
        "label": cluster.name,
        "style": {"galaxy": galaxy.name, "icon": icon_class(galaxy.icon)},
        "galaxy_type": galaxy.type,
        "description": _shorten(cluster.description),
        "id": cluster.id,
        "in_use": True,
    }


def search_clusters(term, galaxy_type=None, limit=None, usage=None):
    query = Cluster.query.join(Galaxy, Galaxy.id == Cluster.galaxy_id)\
        .filter(Cluster.exclude == False, Galaxy.exclude == False)  # noqa: E712
    if usage:
        query = query.filter(Cluster.id.in_(usage.cluster_ids))
    galaxy_type = (galaxy_type or "").strip()
    if galaxy_type:
        if Galaxy.query.filter_by(type=galaxy_type, exclude=False).first() is None:
            return []
        query = query.filter(Galaxy.type == galaxy_type)
    query = query.with_entities(Cluster, Galaxy).order_by(Cluster.name)
    return _search(
        query, Cluster.name, term, lambda r: cluster_row(r[0], r[1]),
        limit_of(limit), 0 if galaxy_type else MIN_TERM,
    )


###############
#  Selection  #
###############

def resolve(tag_ids, cluster_ids, tag_names=None, cluster_tags=None, custom_names=None):
    """The tags and clusters picked in the browser, as the rest of Flowintel handles them.
    By id (editor), or by browser value: tag name, cluster tag (filter)."""
    tags = []
    if tag_ids or tag_names:
        cond = Tags.id.in_(tag_ids or []) | Tags.name.in_(tag_names or [])
        tags = [t.to_json() for t in Tags.query.filter(cond).all()]
    clusters = []
    galaxies = {}
    if cluster_ids or cluster_tags:
        cond = Cluster.id.in_(cluster_ids or []) | Cluster.tag.in_(cluster_tags or [])
        for c in Cluster.query.filter(cond).all():
            clusters.append(c.to_json())
            if c.galaxy_id not in galaxies:
                galaxies[c.galaxy_id] = Galaxy.query.get(c.galaxy_id).to_json()
    custom = []
    if custom_names:
        custom = [t.to_json() for t in Custom_Tags.query.filter(Custom_Tags.name.in_(custom_names)).all()]
    return {"tags": tags, "clusters": clusters, "galaxies": galaxies, "custom_tags": custom}
