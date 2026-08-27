from . import misp_event

module_config = {
    "connector": "misp",
    "case_task": "case",
    "description": "Send a selected subset of case and tasks information to MISP; payload must contain 'selected_case_fields' and/or 'selected_tasks'."
}


def _safe_get(src, key, default=''):
    return src.get(key, default) if isinstance(src, dict) else default


def handler(instance, case, user, case_model=None, db_session=None, payload=None):
    """Create a filtered case according to payload and delegate to misp_event.handler.

    Payload format (examples):
      {
        "selected_case_fields": ["notes","tags","clusters","files","objects","standalone_attributes"],
        "selected_tasks": [ {"uuid": "...", "include_notes": true, "include_resources": false }, ... ]
      }
    If payload is empty or contains no selections, fallback to full misp_event handler.
    """
    # Fallback to full export when no selection provided
    if not payload:
        return misp_event.handler(instance, case, user, case_model=case_model, db_session=db_session)

    scf = payload.get('selected_case_fields', []) or []
    st = payload.get('selected_tasks', []) or []
    if not scf and not st:
        return misp_event.handler(instance, case, user, case_model=case_model, db_session=db_session)

    # Build filtered case
    filtered = {}
    # Minimal required metadata
    filtered['id'] = case.get('id')
    filtered['uuid'] = case.get('uuid')
    filtered['title'] = _safe_get(case, 'title', '')
    filtered['org_name'] = case.get('org_name')
    filtered['org_uuid'] = case.get('org_uuid')
    filtered['status_id'] = case.get('status_id')
    filtered['status'] = case.get('status')

    # Case-level fields selection
    if 'notes' in scf:
        filtered['notes'] = case.get('notes', '')
    else:
        filtered['notes'] = ''

    if 'tags' in scf:
        filtered['tags'] = case.get('tags', [])
    else:
        filtered['tags'] = []

    if 'clusters' in scf:
        filtered['clusters'] = case.get('clusters', [])
    else:
        filtered['clusters'] = []

    if 'objects' in scf:
        filtered['objects'] = case.get('objects', [])
    else:
        filtered['objects'] = []

    if 'standalone_attributes' in scf:
        filtered['standalone_attributes'] = case.get('standalone_attributes', [])
    else:
        filtered['standalone_attributes'] = []

    if 'files' in scf:
        filtered['files'] = case.get('files', [])
    else:
        filtered['files'] = []

    # Build filtered tasks
    filtered_tasks = []
    tasks_by_uuid = {t.get('uuid'): t for t in case.get('tasks', [])}
    for sel in st:
        tuuid = sel.get('uuid')
        task = tasks_by_uuid.get(tuuid)
        if not task:
            continue
        ft = {}
        ft['id'] = task.get('id')
        ft['uuid'] = task.get('uuid')
        ft['title'] = _safe_get(task, 'title', '')
        ft['description'] = task.get('description', '') if sel.get('include_description', True) else ''
        ft['creation_date'] = task.get('creation_date')
        ft['deadline'] = task.get('deadline')
        ft['finish_date'] = task.get('finish_date')
        ft['status'] = task.get('status')
        ft['tags'] = task.get('tags', [])
        # Notes
        if sel.get('include_notes'):
            ft['notes'] = task.get('notes', [])
        else:
            ft['notes'] = []
        # Resources / urls_tools
        if sel.get('include_resources'):
            ft['urls_tools'] = task.get('urls_tools', [])
        else:
            ft['urls_tools'] = []
        # files and subtasks
        ft['files'] = task.get('files', [])
        ft['subtasks'] = task.get('subtasks', [])
        filtered_tasks.append(ft)

    filtered['tasks'] = filtered_tasks

    # Ensure case object list and standalone attributes exist in expected keys
    filtered['objects'] = filtered.get('objects', [])
    filtered['standalone_attributes'] = filtered.get('standalone_attributes', [])

    # Delegate to existing misp_event logic with filtered case
    return misp_event.handler(instance, filtered, user, case_model=case_model, db_session=db_session)


def introspection():
    return module_config
