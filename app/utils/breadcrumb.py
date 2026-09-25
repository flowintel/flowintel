"""Breadcrumb built from the current URL, rendered by macros/page_header.html.

/case/4/edit_task/18  ->  Cases / #4 / Edit task / #18
/admin/add_role       ->  Admin / Roles / New       (FORM_PAGES adds the list)

Each crumb is linked only when its path is a real GET route of the app, so the
breadcrumb never contains dead links. The last crumb (the current page) links to
the page itself, so clicking it reloads the page. Rendered by navbar.html.
"""
from flask import current_app
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

# Labels for URL segments whose name does not read well once humanised
SEGMENT_LABELS = {
    "case": "Cases",
    "custom_tags": "Custom tags",
    "admin": "Admin",
    "orgs": "Organisations",
    "templating": "Templates",
    "cases": "Case templates",
    "tasks": "Task templates",
    "tools": "Tools",
    "note_template_index": "Note templates",
    "connectors": "Connectors",
    "connectors_icons": "Icons",
    "analyzer": "Analyser",
    "misp-modules": "MISP modules",
    "notification": "Notifications",
    "my_assignment": "My assignments",
    "alerting": "Alert triage",
    "account": "My profile",
    "audit_logs": "Audit logs",
    "search_attr": "Search attribute",
    "exporter_view": "Exporter",
    "importer_view": "Importer",
    "create_case": "New case",
    "create_task": "New task",
    "create_note_template_view": "New note template",
    "edit_note_template_view": "Edit",
    "note_template_view": "Note template",
    "add_user": "New user",
    "add_org": "New organisation",
    "add_role": "New role",
    "add_connector": "New connector",
    "add_instance": "New instance",
    "add_icons": "New icon",
    "add": "New",
}

# Same segment, different meaning depending on its parent: (parent, segment) -> label
SEGMENT_LABELS_IN = {
    ("templating", "case"): "Case template",
}

# Form pages whose list is not in the URL: (parent, segment) -> (list label, list URL, action)
# e.g. /admin/add_role -> Admin / Roles / New
FORM_PAGES = {
    ("admin", "add_user"): ("Users", "/admin/users", "New"),
    ("admin", "edit_user"): ("Users", "/admin/users", "Edit"),
    ("admin", "add_org"): ("Organisations", "/admin/orgs", "New"),
    ("admin", "edit_org"): ("Organisations", "/admin/orgs", "Edit"),
    ("admin", "add_role"): ("Roles", "/admin/roles", "New"),
    ("templating", "create_case"): ("Case templates", "/templating/cases", "New"),
    ("templating", "edit_case"): ("Case templates", "/templating/cases", "Edit"),
    ("templating", "create_task"): ("Task templates", "/templating/tasks", "New"),
    ("templating", "edit_task"): ("Task templates", "/templating/tasks", "Edit"),
    ("tools", "create_note_template_view"): ("Note templates", "/tools/note_template_index", "New"),
    ("tools", "edit_note_template_view"): ("Note templates", "/tools/note_template_index", "Edit"),
    ("tools", "note_template_view"): ("Note templates", "/tools/note_template_index", "View"),
    ("connectors", "add_connector"): ("Connectors", "/connectors/", "New"),
    ("connectors", "edit_connector"): ("Connectors", "/connectors/", "Edit"),
    ("connectors", "add_icons"): ("Icons", "/connectors/connectors_icons", "New"),
    ("account", "edit"): (None, None, "Edit"),
    ("case", "create_case"): (None, None, "New"),
    ("case", "edit"): (None, None, "Edit"),
    ("custom_tags", "add"): (None, None, "New"),
}


def _route_exists(path):
    """Return the URL to link to for this path, or None when no GET page serves it.

    A path only counts when the route really describes it: /case/edit matches
    /case/<cid> with cid="edit", which is not a page, so words captured by a URL
    variable are rejected (numeric ids are fine).
    """
    adapter = current_app.url_map.bind("localhost")
    try:
        _, args = adapter.match(path, method="GET")
    except RequestRedirect as redirect:
        # e.g. /case -> /case/ (strict slashes): link to the canonical URL
        return redirect.new_url.replace("http://localhost", "", 1)
    except (NotFound, MethodNotAllowed):
        return None
    if any(not str(value).isdigit() for value in args.values()):
        return None
    return path


def _label(segment, parent=None):
    if segment.isdigit():
        return f"#{segment}"
    if (parent, segment) in SEGMENT_LABELS_IN:
        return SEGMENT_LABELS_IN[(parent, segment)]
    if segment in SEGMENT_LABELS:
        return SEGMENT_LABELS[segment]
    return segment.replace("_", " ").replace("-", " ").strip().capitalize()


def build_breadcrumb(path):
    """List of {"label", "href"} for a URL path; href is None when not linkable."""
    segments = [s for s in (path or "").split("/") if s]
    crumbs = []
    for i, segment in enumerate(segments):
        parent = segments[i - 1] if i else None
        current = "/" + "/".join(segments[: i + 1])
        is_last = i == len(segments) - 1
        label = _label(segment, parent)
        form = FORM_PAGES.get((parent, segment))
        if form:
            list_label, list_href, label = form
            if list_label:
                crumbs.append({"label": list_label, "href": list_href})
        crumbs.append({
            "label": label,
            "href": path if is_last else _route_exists(current),
        })
    return crumbs
