"""
Flowintel Note Variables Resolver
=================================

Resolves @-prefixed variable references in notes and note templates.

SYNTAX REFERENCE
----------------

All variables start with `@` and use dot notation to access properties.

### Case Variables

  @this.case.<property>              Current case (requires case context)
  @case.<id>.<property>              Specific case by ID

  Properties:
    title, description, uuid, id
    status, completed
    creation_date, deadline, finish_date, last_modif
    nb_tasks, time_required
    ticket_id, is_private, recurring_type, recurring_date
    owner_org                        Owner org name
    tags                             Comma-separated tag names
    clusters                         Comma-separated cluster names
    custom_tags                      Comma-separated custom tag names
    notes                            Case notes (raw markdown)
    link                             URL link to the case (/case/<id>)

### Task Variables

  @this.task.<property>              Current task (requires task context)
  @task.<id>.<property>              Specific task by ID

  Properties:
    title, description, uuid, id
    status, completed
    creation_date, deadline, finish_date, last_modif
    case_id, case_title
    nb_notes, time_required
    tags                             Comma-separated tag names
    clusters                         Comma-separated cluster names
    custom_tags                      Comma-separated custom tag names
    link                             URL link to the task

### Task by position within current case

  @this.case.tasks.<n>.<property>    Nth task (1-based) in the current case

### Subtask Variables

  @task.<id>.subtasks.<n>.<property> Nth subtask (1-based) of a task
  @this.task.subtasks.<n>.<property> Nth subtask of the current task

  Properties:
    description, completed, id

### Note Variables (task notes)

  @task.<id>.notes.<n>.<property>    Nth note (1-based) of a task
  @this.task.notes.<n>.<property>    Nth note of the current task

  Properties:
    note (content), uuid, id

### MISP Object Variables

  @this.case.misp_objects            List all MISP object names
  @this.case.misp_objects.<n>.name   Nth MISP object name (1-based)
  @this.case.misp_objects.<n>.attributes
                                     Formatted list of attributes
  @case.<id>.misp_objects...         Same for a specific case

### Org Variables

  @this.case.orgs                    Comma-separated org names in the case

### User Variables (assigned to task)

  @task.<id>.assigned_users          Comma-separated user names
  @this.task.assigned_users          Assigned users for the current task

### Date Helpers

  @now                               Current date/time (YYYY-MM-DD HH:MM)
  @today                             Current date (YYYY-MM-DD)
"""

import re
import datetime
from ..db_class.db import (
    Case, Task, Subtask, Note, Status, Org, Case_Org,
    Case_Misp_Object, Misp_Attribute, Task_User, User
)

# Pattern to match @variable references
# Matches @word.word.word... patterns, including numeric and UUID segments
# Stops at whitespace, end of line, or common punctuation that isn't part of the reference
VARIABLE_PATTERN = re.compile(
    r'@((?:this|case|task|now|today)(?:\.[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|\.[a-zA-Z_][a-zA-Z0-9_]*|\.\d+)*)',
    re.MULTILINE
)


def resolve_variables(text: str, case_id: int = None, task_id: int = None, mark: bool = False) -> str:
    """
    Resolve all @-prefixed variable references in the given text.
    
    Args:
        text: The raw note/template text containing @variables
        case_id: The current case ID (for @this.case.* resolution)
        task_id: The current task ID (for @this.task.* resolution)
        mark: If True, wrap resolved values with ⟪ and ⟫ markers so the
              frontend can style them after markdown rendering.
              Only single-line values are marked (multi-line would break
              across HTML elements).
    
    Returns:
        Text with all valid @variables replaced by their resolved values.
        Invalid/unresolvable variables are left unchanged.
    """
    if not text:
        return text
    
    def replacer(match):
        full_match = match.group(0)  # e.g. "@this.case.title"
        var_path = match.group(1)    # e.g. "this.case.title"
        
        try:
            result = _resolve_single(var_path, case_id, task_id)
            if result is not None:
                result_str = str(result)
                if mark and '\n' not in result_str:
                    return f'\u27ea@{var_path}\u2982{result_str}\u27eb'
                return result_str
        except Exception:
            pass
        
        # Return original if can't resolve
        return full_match
    
    return VARIABLE_PATTERN.sub(replacer, text)


# UUID pattern for validation
_UUID_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


def _lookup_entity(model, identifier: str):
    """Look up a Case or Task by numeric ID or UUID string."""
    try:
        entity_id = int(identifier)
        return model.query.get(entity_id)
    except (ValueError, TypeError):
        pass
    # Try UUID lookup
    if _UUID_RE.match(identifier):
        return model.query.filter_by(uuid=identifier).first()
    return None


def _resolve_single(var_path: str, case_id: int = None, task_id: int = None):
    """Resolve a single variable path like 'this.case.title'"""
    parts = var_path.split('.')
    
    if not parts:
        return None
    
    root = parts[0]
    
    # Simple date helpers
    if root == 'now' and len(parts) == 1:
        return datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    
    if root == 'today' and len(parts) == 1:
        return datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d')
    
    # @this.case.* or @this.task.*
    if root == 'this':
        if len(parts) < 3:
            return None
        entity_type = parts[1]
        remaining = parts[2:]
        
        if entity_type == 'case':
            if case_id is None:
                return None
            case = Case.query.get(case_id)
            if not case:
                return None
            return _resolve_case_property(case, remaining)
        
        elif entity_type == 'task':
            if task_id is None:
                return None
            task = Task.query.get(task_id)
            if not task:
                return None
            return _resolve_task_property(task, remaining)
        
        return None
    
    # @case.<id>.<property>
    if root == 'case':
        if len(parts) < 3:
            return None
        case = _lookup_entity(Case, parts[1])
        if not case:
            return None
        return _resolve_case_property(case, parts[2:])
    
    # @task.<id>.<property>
    if root == 'task':
        if len(parts) < 3:
            return None
        task = _lookup_entity(Task, parts[1])
        if not task:
            return None
        return _resolve_task_property(task, parts[2:])
    
    return None


def _resolve_case_property(case: Case, parts: list):
    """Resolve a property path on a Case object"""
    if not parts:
        return None
    
    prop = parts[0]
    
    # Direct scalar properties
    scalar_props = {
        'title': lambda c: c.title,
        'description': lambda c: c.description or '',
        'uuid': lambda c: c.uuid,
        'id': lambda c: c.id,
        'completed': lambda c: 'Yes' if c.completed else 'No',
        'creation_date': lambda c: c.creation_date.strftime('%Y-%m-%d %H:%M') if c.creation_date else '',
        'deadline': lambda c: c.deadline.strftime('%Y-%m-%d %H:%M') if c.deadline else '',
        'finish_date': lambda c: c.finish_date.strftime('%Y-%m-%d %H:%M') if c.finish_date else '',
        'last_modif': lambda c: c.last_modif.strftime('%Y-%m-%d %H:%M') if c.last_modif else '',
        'nb_tasks': lambda c: c.nb_tasks or 0,
        'time_required': lambda c: c.time_required or '',
        'ticket_id': lambda c: c.ticket_id or '',
        'is_private': lambda c: 'Yes' if c.is_private else 'No',
        'recurring_type': lambda c: c.recurring_type or '',
        'recurring_date': lambda c: c.recurring_date.strftime('%Y-%m-%d') if c.recurring_date else '',
        'notes': lambda c: c.notes or '',
        'link': lambda c: f'/case/{c.id}',
    }
    
    if prop in scalar_props and len(parts) == 1:
        return scalar_props[prop](case)
    
    # Status (resolved name)
    if prop == 'status' and len(parts) == 1:
        status = Status.query.get(case.status_id)
        return status.name if status else ''
    
    # Owner org
    if prop == 'owner_org' and len(parts) == 1:
        org = Org.query.get(case.owner_org_id)
        return org.name if org else ''
    
    # Tags
    if prop == 'tags' and len(parts) == 1:
        from ..db_class.db import Tags, Case_Tags
        tags = Tags.query.join(Case_Tags, Case_Tags.tag_id == Tags.id).filter_by(case_id=case.id).all()
        return ', '.join(t.name for t in tags) if tags else ''
    
    # Clusters
    if prop == 'clusters' and len(parts) == 1:
        from ..db_class.db import Cluster, Case_Galaxy_Tags
        clusters = Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.case_id == case.id)\
            .where(Cluster.id == Case_Galaxy_Tags.cluster_id).all()
        return ', '.join(c.name for c in clusters) if clusters else ''
    
    # Custom tags
    if prop == 'custom_tags' and len(parts) == 1:
        from ..db_class.db import Custom_Tags, Case_Custom_Tags
        custom_tags = Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id == Custom_Tags.id)\
            .where(Case_Custom_Tags.case_id == case.id).all()
        return ', '.join(t.name for t in custom_tags) if custom_tags else ''
    
    # Orgs in case
    if prop == 'orgs' and len(parts) == 1:
        orgs = Org.query.join(Case_Org, Case_Org.org_id == Org.id)\
            .filter(Case_Org.case_id == case.id).all()
        return ', '.join(o.name for o in orgs) if orgs else ''
    
    # Tasks by position: @this.case.tasks.<n>.<property>
    if prop == 'tasks':
        if len(parts) < 2:
            # Return count of tasks
            return case.nb_tasks or 0
        try:
            task_index = int(parts[1]) - 1  # 1-based to 0-based
        except ValueError:
            return None
        tasks = Task.query.filter_by(case_id=case.id).order_by(Task.case_order_id).all()
        if task_index < 0 or task_index >= len(tasks):
            return None
        task = tasks[task_index]
        if len(parts) == 2:
            return task.title
        return _resolve_task_property(task, parts[2:])
    
    # MISP objects: @this.case.misp_objects...
    if prop == 'misp_objects':
        misp_objects = Case_Misp_Object.query.filter_by(case_id=case.id)\
            .order_by(Case_Misp_Object.id).all()
        
        if len(parts) == 1:
            # Return comma-separated names
            return ', '.join(o.name for o in misp_objects) if misp_objects else ''
        
        # @this.case.misp_objects.<n>...
        try:
            obj_index = int(parts[1]) - 1  # 1-based
        except ValueError:
            return None
        if obj_index < 0 or obj_index >= len(misp_objects):
            return None
        obj = misp_objects[obj_index]
        
        if len(parts) == 2:
            return obj.name
        
        return _resolve_misp_object_property(obj, parts[2:])
    
    return None


def _resolve_task_property(task: Task, parts: list):
    """Resolve a property path on a Task object"""
    if not parts:
        return None
    
    prop = parts[0]
    
    scalar_props = {
        'title': lambda t: t.title,
        'description': lambda t: t.description or '',
        'uuid': lambda t: t.uuid,
        'id': lambda t: t.id,
        'completed': lambda t: 'Yes' if t.completed else 'No',
        'creation_date': lambda t: t.creation_date.strftime('%Y-%m-%d %H:%M') if t.creation_date else '',
        'deadline': lambda t: t.deadline.strftime('%Y-%m-%d %H:%M') if t.deadline else '',
        'finish_date': lambda t: t.finish_date.strftime('%Y-%m-%d %H:%M') if t.finish_date else '',
        'last_modif': lambda t: t.last_modif.strftime('%Y-%m-%d %H:%M') if t.last_modif else '',
        'case_id': lambda t: t.case_id,
        'nb_notes': lambda t: t.nb_notes or 0,
        'time_required': lambda t: t.time_required or '',
        'link': lambda t: f'/case/{t.case_id}?task={t.id}',
    }
    
    if prop in scalar_props and len(parts) == 1:
        return scalar_props[prop](task)
    
    # Case title shortcut
    if prop == 'case_title' and len(parts) == 1:
        case = Case.query.get(task.case_id)
        return case.title if case else ''
    
    # Status
    if prop == 'status' and len(parts) == 1:
        status = Status.query.get(task.status_id)
        return status.name if status else ''
    
    # Tags
    if prop == 'tags' and len(parts) == 1:
        from ..db_class.db import Tags, Task_Tags
        tags = Tags.query.join(Task_Tags, Task_Tags.tag_id == Tags.id).filter_by(task_id=task.id).all()
        return ', '.join(t.name for t in tags) if tags else ''
    
    # Clusters
    if prop == 'clusters' and len(parts) == 1:
        from ..db_class.db import Cluster, Task_Galaxy_Tags
        clusters = Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.task_id == task.id)\
            .where(Cluster.id == Task_Galaxy_Tags.cluster_id).all()
        return ', '.join(c.name for c in clusters) if clusters else ''
    
    # Custom tags
    if prop == 'custom_tags' and len(parts) == 1:
        from ..db_class.db import Custom_Tags, Task_Custom_Tags
        custom_tags = Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id == Custom_Tags.id)\
            .where(Task_Custom_Tags.task_id == task.id).all()
        return ', '.join(t.name for t in custom_tags) if custom_tags else ''
    
    # Assigned users
    if prop == 'assigned_users' and len(parts) == 1:
        task_users = Task_User.query.filter_by(task_id=task.id).all()
        users = []
        for tu in task_users:
            user = User.query.get(tu.user_id)
            if user:
                name = f"{user.first_name} {user.last_name}".strip()
                users.append(name or user.email)
        return ', '.join(users) if users else ''
    
    # Subtasks: @task.<id>.subtasks.<n>.<property>
    if prop == 'subtasks':
        subtasks = Subtask.query.filter_by(task_id=task.id).order_by(Subtask.task_order_id).all()
        
        if len(parts) == 1:
            # Return count
            return len(subtasks)
        
        try:
            sub_index = int(parts[1]) - 1  # 1-based
        except ValueError:
            return None
        if sub_index < 0 or sub_index >= len(subtasks):
            return None
        subtask = subtasks[sub_index]
        
        if len(parts) == 2:
            return subtask.description or ''
        
        return _resolve_subtask_property(subtask, parts[2:])
    
    # Notes: @task.<id>.notes.<n>.<property>
    if prop == 'notes':
        notes = Note.query.filter_by(task_id=task.id).order_by(Note.task_order_id).all()
        
        if len(parts) == 1:
            return len(notes)
        
        try:
            note_index = int(parts[1]) - 1  # 1-based
        except ValueError:
            return None
        if note_index < 0 or note_index >= len(notes):
            return None
        note = notes[note_index]
        
        if len(parts) == 2:
            return note.note or ''
        
        return _resolve_note_property(note, parts[2:])
    
    return None


def _resolve_subtask_property(subtask: Subtask, parts: list):
    """Resolve a property on a Subtask"""
    if not parts:
        return None
    
    prop = parts[0]
    if len(parts) != 1:
        return None
    
    props = {
        'id': lambda s: s.id,
        'description': lambda s: s.description or '',
        'completed': lambda s: 'Yes' if s.completed else 'No',
    }
    
    if prop in props:
        return props[prop](subtask)
    return None


def _resolve_note_property(note: Note, parts: list):
    """Resolve a property on a Note"""
    if not parts:
        return None
    
    prop = parts[0]
    if len(parts) != 1:
        return None
    
    props = {
        'id': lambda n: n.id,
        'uuid': lambda n: n.uuid,
        'note': lambda n: n.note or '',
    }
    
    if prop in props:
        return props[prop](note)
    return None


def _resolve_misp_object_property(obj: Case_Misp_Object, parts: list):
    """Resolve a property on a MISP Object"""
    if not parts:
        return None
    
    prop = parts[0]
    
    scalar_props = {
        'name': lambda o: o.name,
        'id': lambda o: o.id,
        'template_uuid': lambda o: o.template_uuid,
        'creation_date': lambda o: o.creation_date.strftime('%Y-%m-%d %H:%M') if o.creation_date else '',
        'last_modif': lambda o: o.last_modif.strftime('%Y-%m-%d %H:%M') if o.last_modif else '',
    }
    
    if prop in scalar_props and len(parts) == 1:
        return scalar_props[prop](obj)
    
    # Attributes
    if prop == 'attributes':
        attrs = Misp_Attribute.query.filter_by(case_misp_object_id=obj.id).all()
        
        if len(parts) == 1:
            # Return formatted list
            lines = []
            for attr in attrs:
                lines.append(f"- **{attr.object_relation}** ({attr.type}): {attr.value}")
            return '\n'.join(lines) if lines else ''
        
        # @...attributes.<n>...
        try:
            attr_index = int(parts[1]) - 1  # 1-based
        except ValueError:
            return None
        if attr_index < 0 or attr_index >= len(attrs):
            return None
        attr = attrs[attr_index]
        
        if len(parts) == 2:
            return attr.value
        
        if len(parts) == 3:
            attr_props = {
                'value': lambda a: a.value,
                'type': lambda a: a.type,
                'object_relation': lambda a: a.object_relation,
                'comment': lambda a: a.comment or '',
                'ids_flag': lambda a: 'Yes' if a.ids_flag else 'No',
                'first_seen': lambda a: a.first_seen.strftime('%Y-%m-%d %H:%M') if a.first_seen else '',
                'last_seen': lambda a: a.last_seen.strftime('%Y-%m-%d %H:%M') if a.last_seen else '',
                'id': lambda a: a.id,
            }
            if parts[2] in attr_props:
                return attr_props[parts[2]](attr)
        
        return None
    
    return None


def get_syntax_reference() -> str:
    """Return the complete syntax reference as markdown."""
    return """# Flowintel Note Variables Reference

## Quick Start
Write `@this.case.title` in your notes to display the current case title.
In **edit mode**, you see the raw `@this.case.title` syntax.
In **render/preview mode**, it resolves to the actual value.

---

## Case Variables

| Variable | Description |
|----------|-------------|
| `@this.case.title` | Current case title |
| `@this.case.description` | Current case description |
| `@this.case.id` | Current case ID |
| `@this.case.uuid` | Current case UUID |
| `@this.case.status` | Current case status name |
| `@this.case.completed` | Whether case is completed (Yes/No) |
| `@this.case.creation_date` | Case creation date |
| `@this.case.deadline` | Case deadline |
| `@this.case.finish_date` | Case finish date |
| `@this.case.last_modif` | Last modification date |
| `@this.case.nb_tasks` | Number of tasks |
| `@this.case.time_required` | Time required |
| `@this.case.ticket_id` | External ticket ID |
| `@this.case.is_private` | Whether case is private (Yes/No) |
| `@this.case.owner_org` | Owner organization name |
| `@this.case.tags` | All tags (comma-separated) |
| `@this.case.clusters` | All galaxy clusters (comma-separated) |
| `@this.case.custom_tags` | All custom tags (comma-separated) |
| `@this.case.orgs` | Organizations in the case (comma-separated) |
| `@this.case.notes` | Case notes content |
| `@this.case.link` | URL link to the case |
| `@this.case.recurring_type` | Recurring type |
| `@this.case.recurring_date` | Recurring date |

Use `@case.<id>.<property>` to reference a **different case** by its ID.
Example: `@case.42.title` → title of case #42.

---

## Task Variables

| Variable | Description |
|----------|-------------|
| `@this.task.title` | Current task title |
| `@this.task.description` | Current task description |
| `@this.task.id` | Current task ID |
| `@this.task.uuid` | Current task UUID |
| `@this.task.status` | Current task status name |
| `@this.task.completed` | Whether task is completed (Yes/No) |
| `@this.task.creation_date` | Task creation date |
| `@this.task.deadline` | Task deadline |
| `@this.task.finish_date` | Task finish date |
| `@this.task.last_modif` | Last modification date |
| `@this.task.case_id` | Parent case ID |
| `@this.task.case_title` | Parent case title |
| `@this.task.nb_notes` | Number of notes |
| `@this.task.time_required` | Time required |
| `@this.task.assigned_users` | Assigned users (comma-separated) |
| `@this.task.tags` | All tags (comma-separated) |
| `@this.task.clusters` | All galaxy clusters (comma-separated) |
| `@this.task.custom_tags` | All custom tags (comma-separated) |
| `@this.task.link` | URL link to the task |

Use `@task.<id>.<property>` to reference a **different task** by its ID.
Example: `@task.10.title` → title of task #10.

---

## Tasks within a Case

| Variable | Description |
|----------|-------------|
| `@this.case.tasks` | Number of tasks in the case |
| `@this.case.tasks.<n>.title` | Title of the Nth task (1-based) |
| `@this.case.tasks.<n>.status` | Status of the Nth task |
| `@this.case.tasks.<n>.<property>` | Any task property on the Nth task |

---

## Subtasks

| Variable | Description |
|----------|-------------|
| `@this.task.subtasks` | Number of subtasks |
| `@this.task.subtasks.<n>.description` | Description of Nth subtask (1-based) |
| `@this.task.subtasks.<n>.completed` | Whether Nth subtask is completed |
| `@task.<id>.subtasks.<n>.<property>` | Subtask of a specific task |

---

## Task Notes

| Variable | Description |
|----------|-------------|
| `@this.task.notes` | Number of notes in current task |
| `@this.task.notes.<n>.note` | Content of the Nth note (1-based) |
| `@this.task.notes.<n>.uuid` | UUID of the Nth note |
| `@task.<id>.notes.<n>.<property>` | Note of a specific task |

---

## MISP Objects

| Variable | Description |
|----------|-------------|
| `@this.case.misp_objects` | All MISP object names (comma-separated) |
| `@this.case.misp_objects.<n>` | Name of the Nth object (1-based) |
| `@this.case.misp_objects.<n>.name` | Name of the Nth object |
| `@this.case.misp_objects.<n>.template_uuid` | Template UUID |
| `@this.case.misp_objects.<n>.creation_date` | Creation date |
| `@this.case.misp_objects.<n>.attributes` | Formatted list of all attributes |
| `@this.case.misp_objects.<n>.attributes.<m>` | Value of the Mth attribute |
| `@this.case.misp_objects.<n>.attributes.<m>.value` | Attribute value |
| `@this.case.misp_objects.<n>.attributes.<m>.type` | Attribute type |
| `@this.case.misp_objects.<n>.attributes.<m>.object_relation` | Object relation |
| `@this.case.misp_objects.<n>.attributes.<m>.comment` | Attribute comment |

Use `@case.<id>.misp_objects...` for a different case.

---

## Date Helpers

| Variable | Description |
|----------|-------------|
| `@now` | Current date and time (YYYY-MM-DD HH:MM) |
| `@today` | Current date (YYYY-MM-DD) |

---

## Usage Examples

```markdown
# Report for @this.case.title

**Case ID:** @this.case.id
**Status:** @this.case.status
**Deadline:** @this.case.deadline
**Owner:** @this.case.owner_org
**Tags:** @this.case.tags

## Tasks Summary
Total tasks: @this.case.tasks

### First Task
- **Title:** @this.case.tasks.1.title
- **Status:** @this.case.tasks.1.status
- **Assigned to:** @this.case.tasks.1.assigned_users

## Related Case
See also: @case.42.title (@case.42.status)

## MISP Objects
@this.case.misp_objects.1.attributes

---
*Report generated on @now*
```
"""
