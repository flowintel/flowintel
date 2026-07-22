import calendar
from io import BytesIO

from pymisp import PyMISP
from werkzeug.datastructures import FileStorage
from ..db_class.db import *
from .. import db
import uuid
import json
import datetime
import traceback
from ..utils import utils, jsonschema_flowintel
from ..case.TaskCore import TaskModel
from ..case.CaseCore import CaseModel
from ..templating.TemplateCase import TemplateModel
from ..templating.TaskTemplateCore import TaskModel as TaskTemplateModel
from sqlalchemy import or_
from ..utils import misp_object_helper
from  ..connectors import connectors_core as ConnectorModel
from ..custom_tags import custom_tags_core as CustomModel
from ..case.common_core import check_user_in_private_cases

DATETIME_FORMAT_FULL = '%Y-%m-%d %H:%M'


def _parse_misp_datetime(value):
    """Best-effort conversion of a MISP timestamp-like value into datetime."""
    if isinstance(value, datetime.datetime):
        return value
    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', DATETIME_FORMAT_FULL):
        try:
            return datetime.datetime.strptime(str(value), fmt)
        except Exception:
            continue
    return None


def _import_event_standalone_attributes(case, event, instance_id, selected_attribute_uuids=None):
    """Create case-level standalone MISP attributes from an event."""
    standalone_attr_uuid_list = []
    selected_attribute_uuids = set(selected_attribute_uuids or [])

    for event_attr in getattr(event, 'attributes', []):
        if event_attr.object_id and int(event_attr.object_id) != 0:
            continue
        if selected_attribute_uuids and event_attr.uuid not in selected_attribute_uuids:
            continue

        sa_attr = Misp_Attribute(
            case_misp_object_id=None,
            case_id=case.id,
            value=str(event_attr.value),
            type=event_attr.type,
            object_relation=getattr(event_attr, "object_relation", "") or "",
            first_seen=_parse_misp_datetime(getattr(event_attr, "first_seen", None)),
            last_seen=_parse_misp_datetime(getattr(event_attr, "last_seen", None)),
            comment=event_attr.comment or "",
            ids_flag=event_attr.to_ids or False,
            disable_correlation=getattr(event_attr, 'disable_correlation', False) or False,
            creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc)
        )
        db.session.add(sa_attr)
        db.session.commit()
        standalone_attr_uuid_list.append({"attribute_id": sa_attr.id, "uuid": event_attr.uuid})

    if standalone_attr_uuid_list:
        CaseModel.result_standalone_attr_module(standalone_attr_uuid_list, instance_id=instance_id, case_id=case.id)


def case_creation_from_importer(case, current_user):
    if not utils.validate_importer_json(case, jsonschema_flowintel.caseSchema):
        return {"message": f"Case '{case['title']}' format not okay"}

    standalone_attrs = case.get("standalone_attributes")
    alias_standalone_attrs = case.get("misp-attributes")
    if standalone_attrs is None:
        standalone_attrs = alias_standalone_attrs if alias_standalone_attrs is not None else []
    elif isinstance(standalone_attrs, list) and len(standalone_attrs) == 0 and isinstance(alias_standalone_attrs, list) and len(alias_standalone_attrs) > 0:
        standalone_attrs = alias_standalone_attrs
    if standalone_attrs is None:
        standalone_attrs = []
    if not isinstance(standalone_attrs, list):
        return {"message": f"Case '{case['title']}': standalone attributes format not okay"}

    for task in case.get("tasks", []):
        if not utils.validate_importer_json(task, jsonschema_flowintel.taskSchema):
            return {"message": f"Task '{task['title']}' format not okay"}
        
    for misp_obj in case.get("misp-objects", []):
        if not utils.validate_importer_json(misp_obj, jsonschema_flowintel.mispObjectSchema):
            return {"message": f"MISP-OBject '{misp_obj['name']}' format not okay"}

        for attr in misp_obj.get("attributes", []):
            if not utils.validate_importer_json(attr, jsonschema_flowintel.mispAttrSchema):
                return {"message": f"MISP-Attribute '{attr['value']}' format not okay"}

    for attr in standalone_attrs:
        if not utils.validate_importer_json(attr, jsonschema_flowintel.mispAttrSchema):
            return {"message": f"Standalone MISP-Attribute '{attr.get('value', '')}' format not okay"}
        if not attr.get("value") or not attr.get("type"):
            return {"message": f"Case '{case['title']}': standalone MISP attributes require 'value' and 'type'"}

    # Keep one normalized key for the DB creation stage.
    case["standalone_attributes"] = standalone_attrs
            
    if "tasks_template" in case:
        return {"message": "'tasks_template' field is not allowed in case import, only 'tasks'."}


    #######################
    ## Case Verification ##
    #######################

    ## Caseformat is valid
    # title
    if Case.query.filter_by(title=case["title"]).first():
        return {"message": f"Case Title '{case['title']}' already exist"}
    # deadline
    if case["deadline"]:
        try:
            loc_date = datetime.datetime.strptime(case["deadline"], DATETIME_FORMAT_FULL)
            case["deadline_date"] = loc_date.date()
            case["deadline_time"] = loc_date.time()
        except Exception as e:
            print(e)
            return {"message": f"Case '{case['title']}': deadline bad format, %Y-%m-%d %H:%M"}
    else:
        case["deadline_date"] = ""
        case["deadline_time"] = ""
    # recurring_date
    if case["recurring_date"]:
        if case["recurring_type"]:
            try:
                datetime.datetime.strptime(case["recurring_date"], DATETIME_FORMAT_FULL)
            except ValueError:
                return {"message": f"Case '{case['title']}': recurring_date bad format, %Y-%m-%d"}
        else:
            return {"message": f"Case '{case['title']}': recurring_type is missing"}
    # recurring_type
    if case["recurring_type"] and not case["recurring_date"]:
        return {"message": f"Case '{case['title']}': recurring_date is missing"}
    # uuid
    if Case.query.filter_by(uuid=case["uuid"]).first():
        case["uuid"] = str(uuid.uuid4())

    # tags
    for tag in case.get("tags", []):
        if not utils.check_tag(tag):
            return {"message": f"Case '{case['title']}': tag '{tag}' doesn't exist"}
    
    # Clusters
    for i in range(0, len(case.get("clusters", []))):
        case["clusters"][i] = case["clusters"][i]["name"]

    # Custom tags
    if case.get("custom_tags"):
        loc_custom_tags = []
        for tag in case.get("custom_tags", []):
            if isinstance(tag, dict):
                loc_custom_tags.append(tag.get("name"))
            else:
                loc_custom_tags.append(tag)
        case["custom_tags"] = loc_custom_tags
    else:
        case["custom_tags"] = []
        
    
    #######################
    ## Task Verification ##
    #######################

    ## Task format is valid
    for task in case["tasks"]:
        if Task.query.filter_by(uuid=task["uuid"]).first():
            task["uuid"] = str(uuid.uuid4())

        if task["deadline"]:
            try:
                loc_date = datetime.datetime.strptime(task["deadline"], DATETIME_FORMAT_FULL)
                task["deadline_date"] = loc_date.date()
                task["deadline_time"] = loc_date.time()
            except ValueError:
                return {"message": f"Task '{task['title']}': deadline bad format, %Y-%m-%d %H:%M"}
        else:
            task["deadline_date"] = ""
            task["deadline_time"] = ""

        for tag in task.get("tags", []):
            if not utils.check_tag(tag):
                return {"message": f"Task '{task['title']}': tag '{tag}' doesn't exist"}
            
        # Clusters
        for i in range(0, len(task.get("clusters", []))):
            task["clusters"][i] = task["clusters"][i]["name"]
        
        # Custom tags
        if task.get("custom_tags"):
            loc_custom_tags = []
            for tag in task.get("custom_tags", []):
                if isinstance(tag, dict):
                    loc_custom_tags.append(tag.get("name"))
                else:
                    loc_custom_tags.append(tag)
            task["custom_tags"] = loc_custom_tags
        else:
            task["custom_tags"] = []

    #################
    ## DB Creation ##
    ################

    ## Case creation
    case_created = CaseModel.create_case(case, current_user)
    if case["notes"]:
        CaseModel.modify_note_core(case_created.id, current_user, case["notes"])

    ## Task creation
    created_tasks_map = {}
    for task in case.get("tasks", []):
        task_created = TaskModel.create_task(task, case_created.id, current_user)
        # keep mapping from task uuid -> created task id for later linking
        try:
            created_tasks_map[task["uuid"]] = task_created.id
        except Exception:
            pass
        # record created id on the task dict to avoid relying on possibly-empty uuids
        try:
            task["_created_id"] = task_created.id
        except Exception:
            pass
        for note in task.get("notes", []):
            loc_note = TaskModel.create_note(task_created.id, current_user)
            TaskModel.modif_note_core(task_created.id, current_user, note["note"], loc_note.id)
        
        for subtask in task.get("subtasks", []):
            TaskModel.create_subtask(task_created.id, subtask["description"], current_user)
        
        for urls_tools in task.get("urls_tools", []):
            TaskModel.create_url_tool(task_created.id, urls_tools["name"], current_user)

    # Create MISP objects and link to tasks when task links are present in the import payload
    created_objects_by_key = {}
    for misp_object in case.get("misp-objects", []):
        misp_object["object-template"] = {"name": misp_object["name"], "uuid": misp_object["template_uuid"]}
        # collect task ids that reference this object in the imported tasks
        task_ids = set()
        for task in case.get("tasks", []):
            for link in task.get("misp_object_links", []):
                if link.get("misp_object_template_uuid") == misp_object.get("template_uuid") and link.get("misp_object_name") == misp_object.get("name"):
                    tid = task.get("_created_id") or created_tasks_map.get(task.get("uuid"))
                    if tid:
                        task_ids.add(tid)
        if task_ids:
            misp_object["task_ids"] = list(task_ids)
        created_obj = CaseModel.create_misp_object(case_created.id, misp_object, current_user)
        # store created object for attribute matching (keyed by template_uuid+name)
        try:
            created_objects_by_key[(created_obj.template_uuid, created_obj.name)] = created_obj.id
        except Exception:
            pass

    for attr in case.get("standalone_attributes", []):
        # collect task ids that reference this standalone attribute in the imported tasks
        task_ids = set()
        for task in case.get("tasks", []):
            for alink in task.get("misp_attribute_links", []):
                if alink.get("misp_attribute_uuid") == attr.get("uuid"):
                    tid = task.get("_created_id") or created_tasks_map.get(task.get("uuid"))
                    if tid:
                        task_ids.add(tid)
        if task_ids:
            attr["task_ids"] = list(task_ids)
        CaseModel.create_standalone_attribute(case_created.id, attr, current_user)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return {"id": case_created.id}


def case_template_creation_from_importer(template):
    if not utils.validate_importer_json(template, jsonschema_flowintel.caseTemplateSchema):
        return {"message": f"Case template '{template['title']}' format not okay"}
    for task in template.get("tasks_template", []):
        if not utils.validate_importer_json(task, jsonschema_flowintel.taskTemplateSchema):
            return {"message": f"Task Template '{task['title']}' format not okay"}
        
    #######################
    ## Case Verification ##
    #######################

    ## Caseformat is valid
    # title
    if Case_Template.query.filter_by(title=template["title"]).first():
        return {"message": f"Case Template Title '{template['title']}' already exist"}
    
    # uuid
    if Case_Template.query.filter_by(uuid=template["uuid"]).first():
        template["uuid"] = str(uuid.uuid4())

    # tags
    for tag in template["tags"]:
        if not utils.check_tag(tag):
            return {"message": f"Case Template '{template['title']}': tag '{tag}' doesn't exist"}
    
    # Clusters
    for i in range(0, len(template["clusters"])):
        template["clusters"][i] = template["clusters"][i]["name"]

    # Custom tags
    if template.get("custom_tags"):
        loc_custom_tags = []
        for tag in template.get("custom_tags", []):
            if isinstance(tag, dict):
                loc_custom_tags.append(tag.get("name"))
            else:
                loc_custom_tags.append(tag)
        template["custom_tags"] = loc_custom_tags
    else:
        template["custom_tags"] = []
        
    
    #######################
    ## Task Verification ##
    #######################

    ## Task format is valid
    for task in template.get("tasks_template", []):
        if Task.query.filter_by(uuid=task["uuid"]).first():
            task["uuid"] = str(uuid.uuid4())

        for tag in task["tags"]:
            if not utils.check_tag(tag):
                return {"message": f"Task '{task['title']}': tag '{tag}' doesn't exist"}
            
        # Clusters
        for i in range(0, len(task["clusters"])):
            task["clusters"][i] = task["clusters"][i]["name"]
        
        # Custom tags
        if task.get("custom_tags"):
            loc_custom_tags = []
            for tag in task.get("custom_tags", []):
                if isinstance(tag, dict):
                    loc_custom_tags.append(tag.get("name"))
                else:
                    loc_custom_tags.append(tag)
            task["custom_tags"] = loc_custom_tags
        else:
            task["custom_tags"] = []

    #################
    ## DB Creation ##
    ################

    ## Case creation
    template["tasks"] = []
    case_created = TemplateModel.create_case(template)
    if template["notes"]:
        TemplateModel.modif_note_core(case_created.id, template["notes"])

    ## Task creation
    for task in template.get("tasks_template", []):
        task_created = TaskTemplateModel.add_task_template_core(task)
        TemplateModel.add_task_case_template({"tasks": [task_created.id]}, case_created.id)
        if task["notes"]:
            for note in task["notes"]:
                loc_note = TaskTemplateModel.create_note(task_created.id)
                TaskTemplateModel.modif_note_core(task_created.id, note["note"], loc_note.id)
        
        if task["subtasks"]:
            for subtask in task["subtasks"]:
                TaskTemplateModel.create_subtask(task_created.id, subtask["description"])
        
        if task["urls_tools"]:
            for urls_tools in task["urls_tools"]:
                TaskTemplateModel.create_url_tool(task_created.id, urls_tools["name"])



    
def importer_core(files_list, current_user, importer_type, create_custom_tags=False):
    results = []
    for file in files_list:
        filename = files_list[file].filename
        if filename:
            try:
                file_data = json.loads(files_list[file].read().decode())
                # Create missing custom tags
                if create_custom_tags:
                    if isinstance(file_data, list):
                        for case in file_data:
                            CustomModel.ensure_custom_tags_for_case_payload(case)
                    elif isinstance(file_data, dict):
                        CustomModel.ensure_custom_tags_for_case_payload(file_data)

                items = file_data if isinstance(file_data, list) else [file_data]
                for item in items:
                    title = item.get("title", filename)
                    if importer_type == 'case':
                        res = case_creation_from_importer(item, current_user)
                    elif importer_type == 'template':
                        res = case_template_creation_from_importer(item)
                    else:
                        res = None
                    if res and "message" in res:
                        results.append({"status": "error", "filename": filename, "title": title, "message": res["message"]})
                    else:
                        entry = {"status": "success", "filename": filename, "title": title}
                        if res and "id" in res:
                            entry["id"] = res["id"]
                        results.append(entry)
            except Exception as e:
                tb = traceback.format_exc()
                print(tb)
                results.append({
                    "status": "error",
                    "filename": filename,
                    "title": filename,
                    "message": str(e),
                    "traceback": tb,
                })
    return {"results": results}


def chart_dict_constructor(input_dict):
    loc_dict = []
    for elem in input_dict:
        loc_dict.append({
            "calendar": elem,
            "count": input_dict[elem]
        })
    return loc_dict

def days_cutoff(days):
    try:
        days = int(days)
    except (TypeError, ValueError):
        return None
    if days <= 0:
        return None
    return datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=days)


def filter_cases_by_date(cases, cutoff):
    if cutoff is None:
        return cases
    return [c for c in cases if c.creation_date and c.creation_date >= cutoff]

def stats_core(cases):
    cases_opened_month = {month: 0 for month in calendar.month_name if month}
    cases_opened_year = {}
    cases_closed_month = {month: 0 for month in calendar.month_name if month}
    cases_closed_year = {}
    cases_elapsed_time = {}
    cases_resolution_total = 0
    total_opened_cases = 0
    total_closed_cases = 0
    overdue_cases = 0

    tasks_opened_month = {month: 0 for month in calendar.month_name if month}
    tasks_opened_year = {}
    tasks_closed_month = {month: 0 for month in calendar.month_name if month}
    tasks_closed_year = {}
    tasks_elapsed_time = {}
    tasks_resolution_total = 0
    tasks_per_case = {}
    total_opened_tasks = 0
    total_closed_tasks = 0
    overdue_tasks = 0
    due_soon_tasks = 0

    current_year = datetime.datetime.now().year
    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
    upcoming_cutoff = now + datetime.timedelta(days=7)
    top_cases_by_tasks = []

    for case in cases:
        if case.creation_date.year == current_year:
            cases_opened_month[case.creation_date.strftime("%B")] += 1
            if case.finish_date:
                cases_closed_month[case.finish_date.strftime("%B")] += 1

        if case.creation_date.year not in cases_opened_year: # initialize dict
            cases_opened_year[case.creation_date.year] = 0
        cases_opened_year[case.creation_date.year] += 1

        if case.finish_date:
            if case.finish_date.year not in cases_closed_year: # initialize dict
                cases_closed_year[case.finish_date.year] = 0
            cases_closed_year[case.finish_date.year] += 1

            loc = case.finish_date - case.creation_date
            loc = loc.days // 7
            if loc not in cases_elapsed_time:
                cases_elapsed_time[loc] = 0
            cases_elapsed_time[loc] += 1
            cases_resolution_total += loc

            total_closed_cases += 1
        else:
            total_opened_cases += 1
            if case.deadline and case.deadline < now:
                overdue_cases += 1

        case_tasks = list(case.tasks)
        case_open_tasks = 0
        case_closed_tasks = 0

        # Tasks part
        for task in case_tasks:
            if task.creation_date.year == current_year:
                tasks_opened_month[task.creation_date.strftime("%B")] += 1
                if task.finish_date:
                    tasks_closed_month[task.finish_date.strftime("%B")] += 1

            if task.creation_date.year not in tasks_opened_year: # initialize dict
                tasks_opened_year[task.creation_date.year] = 0
            tasks_opened_year[task.creation_date.year] += 1

            if task.finish_date:
                if task.finish_date.year not in tasks_closed_year: # initialize dict
                    tasks_closed_year[task.finish_date.year] = 0
                tasks_closed_year[task.finish_date.year] += 1

                loc = task.finish_date - task.creation_date
                loc = loc.days // 7
                if loc not in tasks_elapsed_time:
                    tasks_elapsed_time[loc] = 0
                tasks_elapsed_time[loc] += 1
                tasks_resolution_total += loc

                total_closed_tasks += 1
                case_closed_tasks += 1
            else:
                total_opened_tasks += 1
                case_open_tasks += 1
                if task.deadline:
                    if task.deadline < now:
                        overdue_tasks += 1
                    elif task.deadline <= upcoming_cutoff:
                        due_soon_tasks += 1

        task_count = case.nb_tasks if case.nb_tasks is not None else len(case_tasks)
        if task_count not in tasks_per_case:
            tasks_per_case[task_count] = 0
        tasks_per_case[task_count] += 1

        top_cases_by_tasks.append({
            "id": case.id,
            "title": case.title,
            "task_count": task_count,
            "open_tasks": case_open_tasks,
            "closed_tasks": case_closed_tasks,
            "completed": bool(case.completed),
            "last_modif": case.last_modif.strftime(DATETIME_FORMAT_FULL) if case.last_modif else "",
        })


    loc_cases_opened_month = chart_dict_constructor(cases_opened_month)
    loc_cases_opened_year = chart_dict_constructor(cases_opened_year)

    loc_cases_closed_month = chart_dict_constructor(cases_closed_month)
    loc_cases_closed_year = chart_dict_constructor(cases_closed_year)

    loc_cases_elapsed_time = chart_dict_constructor(cases_elapsed_time)

    loc_tasks_opened_month = chart_dict_constructor(tasks_opened_month)
    loc_tasks_opened_year = chart_dict_constructor(tasks_opened_year)

    loc_tasks_closed_month = chart_dict_constructor(tasks_closed_month)
    loc_tasks_closed_year = chart_dict_constructor(tasks_closed_year)

    loc_tasks_elapsed_time = chart_dict_constructor(tasks_elapsed_time)
    loc_tasks_per_case = chart_dict_constructor(tasks_per_case)

    total_cases = total_opened_cases + total_closed_cases
    total_tasks = total_opened_tasks + total_closed_tasks
    top_cases_by_tasks.sort(key=lambda row: (-row["task_count"], row["title"].lower()))

    return {"cases-opened-month": loc_cases_opened_month, "cases-opened-year": loc_cases_opened_year,
            "cases-closed-month": loc_cases_closed_month, "cases-closed-year": loc_cases_closed_year,
            "cases-elapsed-time": loc_cases_elapsed_time,
            "total_opened_cases": total_opened_cases, "total_closed_cases": total_closed_cases,
            "total_cases": total_cases,
            "case_closure_rate": round((total_closed_cases / total_cases) * 100, 1) if total_cases else 0,
            "avg_case_resolution_weeks": round(cases_resolution_total / total_closed_cases, 1) if total_closed_cases else None,
            "overdue_cases": overdue_cases,
            "tasks-opened-month": loc_tasks_opened_month, "tasks-opened-year": loc_tasks_opened_year,
            "tasks-closed-month": loc_tasks_closed_month, "tasks-closed-year": loc_tasks_closed_year,
            "tasks-elapsed-time": loc_tasks_elapsed_time, "tasks-per-case": loc_tasks_per_case,
            "total_opened_tasks": total_opened_tasks, "total_closed_tasks": total_closed_tasks,
            "total_tasks": total_tasks,
            "task_closure_rate": round((total_closed_tasks / total_tasks) * 100, 1) if total_tasks else 0,
            "avg_task_resolution_weeks": round(tasks_resolution_total / total_closed_tasks, 1) if total_closed_tasks else None,
            "overdue_tasks": overdue_tasks,
            "due_soon_tasks": due_soon_tasks,
            "top_cases_by_tasks": top_cases_by_tasks[:5]}

def get_case_by_tags(current_user, cutoff=None):
    cases = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id).all()
    cases = filter_cases_by_date(cases, cutoff)
    dict_case_tag = {}
    dict_case_cluster_tag = {}
    dict_case_custom_tag = {}
    dict_task_tag = {}
    dict_task_cluster_tag = {}
    dict_task_custom_tag = {}

    for case in cases:
        custom = Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id==Custom_Tags.id).filter_by(case_id=case.id).all()
        for c in custom:
            if not c.name in dict_case_custom_tag:
                dict_case_custom_tag[c.name] = 0
            dict_case_custom_tag[c.name] += 1

        tags = Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=case.id).all()
        for t in tags:
            if not t.name in dict_case_tag:
                dict_case_tag[t.name] = 0
            dict_case_tag[t.name] += 1
        
        cluster = Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id==Cluster.id).filter_by(case_id=case.id).all()
        for cl in cluster:
            if not cl.tag in dict_case_cluster_tag:
                dict_case_cluster_tag[cl.tag] = 0
            dict_case_cluster_tag[cl.tag] += 1

        for task in case.tasks:
            custom = Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id==Custom_Tags.id).filter_by(task_id=task.id).all()
            for c in custom:
                if not c.name in dict_task_custom_tag:
                    dict_task_custom_tag[c.name] = 0
                dict_task_custom_tag[c.name] += 1

            tags = Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=task.id).all()
            for t in tags:
                if not t.name in dict_task_tag:
                    dict_task_tag[t.name] = 0
                dict_task_tag[t.name] += 1
            
            cluster = Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id==Cluster.id).filter_by(task_id=task.id).all()
            for cl in cluster:
                if not cl.tag in dict_task_cluster_tag:
                    dict_task_cluster_tag[cl.tag] = 0
                dict_task_cluster_tag[cl.tag] += 1


    return {"case_custom_tags": chart_dict_constructor(dict_case_custom_tag), 
            "case_tags": chart_dict_constructor(dict_case_tag), 
            "case_clusters": chart_dict_constructor(dict_case_cluster_tag),
            "task_custom_tags": chart_dict_constructor(dict_task_custom_tag), 
            "task_tags": chart_dict_constructor(dict_task_tag), 
            "task_clusters": chart_dict_constructor(dict_task_cluster_tag)}


def get_tag_galaxy_top_stats(current_user, limit=10, cutoff=None):
    cases = Case.query.join(Case_Org, Case_Org.case_id==Case.id).where(Case_Org.org_id==current_user.org_id).all()
    cases = filter_cases_by_date(cases, cutoff)

    case_tag_map = {}
    case_cluster_map = {}
    task_tag_map = {}
    task_cluster_map = {}

    for case in cases:
        case_info = {"id": case.id, "title": case.title, "description": case.description or ""}

        for c in Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id==Custom_Tags.id).filter_by(case_id=case.id).all():
            e = case_tag_map.setdefault(c.name, {"count": 0, "cases": []})
            e["count"] += 1
            e["cases"].append(case_info)

        for t in Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=case.id).all():
            e = case_tag_map.setdefault(t.name, {"count": 0, "cases": []})
            e["count"] += 1
            e["cases"].append(case_info)

        for cl in Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id==Cluster.id).filter_by(case_id=case.id).all():
            e = case_cluster_map.setdefault(cl.tag, {"count": 0, "cases": [], "name": cl.name})
            e["count"] += 1
            e["cases"].append(case_info)

        for task in case.tasks:
            task_info = {"id": task.id, "title": task.title, "case_id": task.case_id}

            for c in Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id==Custom_Tags.id).filter_by(task_id=task.id).all():
                e = task_tag_map.setdefault(c.name, {"count": 0, "tasks": []})
                e["count"] += 1
                e["tasks"].append(task_info)

            for t in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=task.id).all():
                e = task_tag_map.setdefault(t.name, {"count": 0, "tasks": []})
                e["count"] += 1
                e["tasks"].append(task_info)

            for cl in Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id==Cluster.id).filter_by(task_id=task.id).all():
                e = task_cluster_map.setdefault(cl.tag, {"count": 0, "tasks": [], "name": cl.name})
                e["count"] += 1
                e["tasks"].append(task_info)

    def top_n(d):
        rows = sorted(d.items(), key=lambda x: x[1]["count"], reverse=True)[:limit]
        return [{"tag": k, **v} for k, v in rows]

    return {
        "case_tags": top_n(case_tag_map),
        "case_clusters": top_n(case_cluster_map),
        "task_tags": top_n(task_tag_map),
        "task_clusters": top_n(task_cluster_map),
    }


def get_misp_stats(current_user, cutoff=None, limit=10):
    """Aggregate visible MISP objects and standalone attributes for the stats UI."""
    cases = Case.query.join(Case_Org, Case_Org.case_id == Case.id).where(Case_Org.org_id == current_user.org_id).all()
    cases = check_user_in_private_cases(cases, current_user)
    cases = filter_cases_by_date(cases, cutoff)
    case_ids = [case.id for case in cases]

    if not case_ids:
        return {
            "total_objects": 0,
            "unique_object_names": 0,
            "total_object_attributes": 0,
            "total_standalone_attributes": 0,
            "linked_task_object_refs": 0,
            "linked_task_attribute_refs": 0,
            "objects_per_case": [],
            "object_names": [],
            "standalone_types": [],
            "standalone_relations": [],
            "top_objects": [],
            "top_standalone_types": [],
            "top_standalone_relations": [],
        }

    case_map = {case.id: {"id": case.id, "title": case.title, "description": case.description or ""} for case in cases}
    case_rows = [{"label": case.title, "count": 0} for case in cases]
    case_row_index = {case.id: idx for idx, case in enumerate(cases)}

    object_name_counts = {}
    standalone_type_counts = {}
    standalone_relation_counts = {}
    top_objects_map = {}
    top_standalone_type_map = {}
    top_standalone_relation_map = {}
    total_object_attributes = 0

    objects = Case_Misp_Object.query.filter(Case_Misp_Object.case_id.in_(case_ids)).all()
    object_ids = [obj.id for obj in objects]

    for obj in objects:
        object_attrs = obj.attributes.all()
        attr_count = len(object_attrs)
        total_object_attributes += attr_count

        case_info = case_map.get(obj.case_id)
        if obj.case_id in case_row_index:
            case_rows[case_row_index[obj.case_id]]["count"] += 1

        name_key = obj.name or "(unnamed object)"
        object_name_counts[name_key] = object_name_counts.get(name_key, 0) + 1

        entry = top_objects_map.setdefault(name_key, {
            "name": name_key,
            "count": 0,
            "attribute_count": 0,
            "cases": [],
        })
        entry["count"] += 1
        entry["attribute_count"] += attr_count
        if case_info and not any(c["id"] == case_info["id"] for c in entry["cases"]):
            entry["cases"].append(case_info)

    standalone_attributes = Misp_Attribute.query.filter(
        Misp_Attribute.case_id.in_(case_ids),
        Misp_Attribute.case_misp_object_id == None,
    ).all()
    standalone_ids = [attr.id for attr in standalone_attributes]

    for attr in standalone_attributes:
        case_info = case_map.get(attr.case_id)
        type_key = attr.type or "(no type)"
        relation_key = attr.object_relation or "(no relation)"

        standalone_type_counts[type_key] = standalone_type_counts.get(type_key, 0) + 1
        standalone_relation_counts[relation_key] = standalone_relation_counts.get(relation_key, 0) + 1

        type_entry = top_standalone_type_map.setdefault(type_key, {
            "name": type_key,
            "count": 0,
            "cases": [],
            "attributes": [],
        })
        type_entry["count"] += 1
        if case_info and not any(c["id"] == case_info["id"] for c in type_entry["cases"]):
            type_entry["cases"].append(case_info)
        type_entry["attributes"].append({
            "id": attr.id,
            "value": attr.value,
            "type": attr.type,
            "case_id": attr.case_id,
            "case_title": case_info["title"] if case_info else "",
        })

        relation_entry = top_standalone_relation_map.setdefault(relation_key, {
            "name": relation_key,
            "count": 0,
            "cases": [],
            "attributes": [],
        })
        relation_entry["count"] += 1
        if case_info and not any(c["id"] == case_info["id"] for c in relation_entry["cases"]):
            relation_entry["cases"].append(case_info)
        relation_entry["attributes"].append({
            "id": attr.id,
            "value": attr.value,
            "type": attr.type,
            "case_id": attr.case_id,
            "case_title": case_info["title"] if case_info else "",
        })

    linked_task_object_refs = Task_Misp_Object.query.filter(Task_Misp_Object.misp_object_id.in_(object_ids)).count() if object_ids else 0
    linked_task_attribute_refs = Task_Misp_Attribute.query.filter(Task_Misp_Attribute.misp_attribute_id.in_(standalone_ids)).count() if standalone_ids else 0

    def _sorted_chart_rows(data_dict):
        return [{"label": key, "count": value} for key, value in sorted(data_dict.items(), key=lambda item: item[1], reverse=True)]

    def _top_rows(data_map):
        rows = sorted(data_map.values(), key=lambda row: row["count"], reverse=True)[:limit]
        for row in rows:
            if "attributes" in row:
                row["attributes"] = row["attributes"][:25]
        return rows

    return {
        "total_objects": len(objects),
        "unique_object_names": len(object_name_counts),
        "total_object_attributes": total_object_attributes,
        "total_standalone_attributes": len(standalone_attributes),
        "linked_task_object_refs": linked_task_object_refs,
        "linked_task_attribute_refs": linked_task_attribute_refs,
        "objects_per_case": case_rows,
        "object_names": _sorted_chart_rows(object_name_counts),
        "standalone_types": _sorted_chart_rows(standalone_type_counts),
        "standalone_relations": _sorted_chart_rows(standalone_relation_counts),
        "top_objects": _top_rows(top_objects_map),
        "top_standalone_types": _top_rows(top_standalone_type_map),
        "top_standalone_relations": _top_rows(top_standalone_relation_map),
    }


########################
# Case from MISP Event #
########################

def get_misp_connector_by_user(user_id):
        connector = ConnectorModel.get_connector_by_name("MISP")
        instances_list = []
        if connector:
            for instance in connector.instances:
                if instance.sharing_scope in {"org", "global"}:
                    loc_instance = instance.to_json()
                    if ConnectorModel.get_user_instance_both(user_id=user_id, instance_id=instance.id):
                        loc_instance["is_user_global_api"] = True
                    instances_list.append(loc_instance)
                elif ConnectorModel.get_user_instance_both(user_id=user_id, instance_id=instance.id):
                    instances_list.append(instance.to_json())
        return instances_list

def check_connection_misp(misp_instance_id: int, current_user: User):
    instance = Connector_Instance.query.get(misp_instance_id)
    if instance:
        loc_api_key = ""
        if instance.global_api_key:
            loc_api_key = instance.global_api_key
        else:
            user_connector_instance = User_Connector_Instance.query.filter_by(user_id=current_user.id,instance_id=instance.id).first()
            if user_connector_instance:
                loc_api_key = user_connector_instance.api_key

        if loc_api_key:
            try:
                misp = PyMISP(instance.url, loc_api_key, ssl=False, timeout=20)
            except Exception:
                return "Error connecting to MISP"
            
            return misp
        return "No config found for the instance"
    return "Instance not found"

def check_event(event_id: str, misp_instance_id: int, current_user: User):
    misp = check_connection_misp(misp_instance_id, current_user)
    if type(misp) == PyMISP:
        event = misp.get_event(event_id, pythonify=True)

        if 'errors' in event:
            return "Event not found on this MISP instance"
        
        return event
    else:
        return misp


_MISP_THREAT_LEVELS = {"1": "High", "2": "Medium", "3": "Low", "4": "Undefined"}
_MISP_ANALYSIS = {"0": "Initial", "1": "Ongoing", "2": "Completed"}
_MISP_DISTRIBUTIONS = {
    "0": "Your organisation only",
    "1": "This community only",
    "2": "Connected communities",
    "3": "All communities",
    "4": "Sharing group",
    "5": "Inherit event",
}


_MISP_FILE_ATTR_TYPES = ("attachment", "malware-sample")


def summarize_misp_event(event):
    """Return a JSON-friendly snapshot of a MISPEvent for the UI preview."""
    data = event.to_dict()

    def _org(key):
        org = data.get(key) or {}
        return {"id": org.get("id"), "name": org.get("name")} if org else None

    galaxies = []
    for galaxy in data.get("Galaxy", []):
        clusters = galaxy.get("GalaxyCluster", [])
        if clusters:
            galaxies.extend(c["value"] for c in clusters if c.get("value"))
        elif galaxy.get("name"):
            galaxies.append(galaxy["name"])

    attributes = [
        {
            "uuid": a.get("uuid"),
            "type": a.get("type"),
            "category": a.get("category"),
            "value": a.get("value"),
            "comment": a.get("comment") or "",
        }
        for a in data.get("Attribute", [])
    ]

    objects = [
        {
            "uuid": o.get("uuid"),
            "name": o.get("name"),
            "comment": o.get("comment") or "",
            "nb_attributes": len(o.get("Attribute", [])),
            "attributes": [
                {"type": a.get("type"), "value": a.get("value")}
                for a in o.get("Attribute", [])
            ],
        }
        for o in data.get("Object", [])
    ]

    nb_files = sum(1 for a in data.get("Attribute", []) if a.get("type") in _MISP_FILE_ATTR_TYPES)
    nb_files += sum(
        1
        for o in data.get("Object", [])
        for a in o.get("Attribute", [])
        if a.get("type") in _MISP_FILE_ATTR_TYPES
    )

    return {
        "id": data.get("id"),
        "info": data.get("info"),
        "published": bool(data.get("published")),
        "creator_org": _org("Orgc"),
        "owner_org": _org("Org"),
        "nb_attributes": len(attributes),
        "nb_objects": len(objects),
        "nb_object_attributes": sum(o["nb_attributes"] for o in objects),
        "nb_reports": len(data.get("EventReport", [])),
        "nb_files": nb_files,
        "tags": [t["name"] for t in data.get("Tag", []) if t.get("name")],
        "galaxies": galaxies,
        "attributes": attributes,
        "objects": objects,
    }


def _build_event_info_markdown(event) -> str:
    data = event.to_dict()
    creator = (data.get("Orgc") or {}).get("name") or ""
    owner = (data.get("Org") or {}).get("name") or ""
    return (
        f"Event: {data.get('info', '')}\n"
        f"Creator org: {creator}\n"
        f"Owner org: {owner}\n"
        f"Date: {data.get('date', '')}\n"
        f"Threat level: {_MISP_THREAT_LEVELS.get(str(data.get('threat_level_id', '')), '')}\n"
        f"Analysis: {_MISP_ANALYSIS.get(str(data.get('analysis', '')), '')}\n"
        f"Distribution level: {_MISP_DISTRIBUTIONS.get(str(data.get('distribution', '')), '')}\n"
    )


def _build_attributes_markdown(event, selected_uuids) -> str:
    attrs = event.to_dict().get("Attribute", [])
    if selected_uuids is not None:
        wanted = set(selected_uuids)
        attrs = [a for a in attrs if a.get("uuid") in wanted]
    if not attrs:
        return "No individual attributes selected."
    lines = [
        "| Type | Category | Value | to_ids | Correlation | Comment |",
        "|------|----------|-------|--------|-------------|---------|",
    ]
    for a in attrs:
        value = (a.get("value") or "").replace("|", "\\|").replace("\n", " ")
        comment = (a.get("comment") or "").replace("|", "\\|").replace("\n", " ")
        to_ids = "Yes" if a.get("to_ids") else "No"
        # MISP stores the inverse flag (`disable_correlation`); show the user-facing one.
        correlation = "No" if a.get("disable_correlation") else "Yes"
        lines.append(
            f"| {a.get('type', '')} | {a.get('category', '')} | {value} | {to_ids} | {correlation} | {comment} |"
        )
    return "\n".join(lines)


def _add_markdown_task(case, title, description, note_markdown, current_user):
    """Create a task on ``case`` containing a single markdown note."""
    task_form = {
        "title": title,
        "description": description,
        "deadline_date": None,
        "deadline_time": None,
        "time_required": 0,
    }
    task = TaskModel.create_task(task_form, case.id, current_user)
    note = TaskModel.create_note(task.id, current_user)
    TaskModel.modif_note_core(task.id, current_user, note_markdown, note.id)
    return task


def _import_misp_attribute_files(misp, event_id, current_user, case):
    """Re-fetch the event with attachments and attach every file attribute to ``case``."""
    results = misp.search(
        controller="events",
        eventid=event_id,
        with_attachments=True,
        pythonify=True,
    )
    if not results:
        return
    event_with_data = results[0]
    file_attrs = [a for a in event_with_data.attributes if a.type in _MISP_FILE_ATTR_TYPES]
    for obj in event_with_data.objects:
        file_attrs.extend(a for a in obj.attributes if a.type in _MISP_FILE_ATTR_TYPES)
    if not file_attrs:
        return

    files_dict = {}
    for idx, attr in enumerate(file_attrs):
        data = getattr(attr, "data", None)
        if not data:
            continue
        # MISPAttribute.data exposes a BytesIO. For malware-sample, attr.value is "filename|md5".
        data.seek(0)
        raw_name = (attr.value or "").split("|", 1)[0].strip()
        filename = raw_name or f"misp_attachment_{idx + 1}"
        files_dict[f"misp_file_{idx}"] = FileStorage(
            stream=data,
            filename=filename,
            content_type="application/octet-stream",
        )
    if files_dict:
        CaseModel.add_file_core(case, files_dict, current_user)



def check_case_misp_event(request_form, current_user) -> str:
    if request_form.get("case_title"):
        if Case.query.filter_by(title=request_form.get("case_title")).first():
            return "Case already exist"
    else:
        return "Case title empty"
    
    if not request_form.get("misp_event_id"):
        return "Need a misp event id"
    
    if not request_form.get("misp_instance_id"):
        return "Need a misp instance"
    
    if not request_form.get("case_template_id"):
        return "Need a case template"
    
    return check_event(request_form.get("misp_event_id"), request_form.get("misp_instance_id"), current_user)

def create_case_misp_event(request_form, current_user):
    """Create a case from a MISP Event"""
    misp = check_connection_misp(request_form.get("misp_instance_id"), current_user)
    if not isinstance(misp, PyMISP):
        # check_connection_misp returns an error string when the instance is missing
        # or the user has neither a global nor a personal API key configured.
        return None
    instance = Connector_Instance.query.get(request_form.get("misp_instance_id"))

    event = misp.get_event(request_form.get("misp_event_id"), pythonify=True)

    case = TemplateModel.create_case_from_template(request_form.get("case_template_id"), request_form.get("case_title"), current_user)

    misp_event_id = request_form.get('misp_event_id')

    case.description = event.info
    case.ticket_id = f"MISP Event: {misp_event_id}"
    case.is_private = True
    case.is_updated_from_misp = True
    db.session.commit()

    for misp_tags in event.tags:
        tag = Tags.query.filter_by(name=misp_tags.name).first()
        if tag and not Case_Tags.query.filter_by(tag_id=tag.id, case_id=case.id).first():
            CaseModel.add_tag(tag, case.id)

    for misp_galaxy in event.galaxies:
        for misp_cluster in misp_galaxy.clusters:
            cluster = Cluster.query.filter_by(tag=misp_cluster.tag_name).first()
            if cluster and not Case_Galaxy_Tags.query.filter_by(cluster_id=cluster.id, case_id=case.id).first():
                CaseModel.add_cluster(cluster, case.id)

    raw_object_uuids = request_form.get("selected_object_uuids")
    selected_object_uuids = set(raw_object_uuids) if isinstance(raw_object_uuids, list) else None
    raw_attribute_uuids = request_form.get("selected_attribute_uuids")
    selected_attribute_uuids = raw_attribute_uuids if isinstance(raw_attribute_uuids, list) else None

    object_uuid_list = {}
    for obje in event.objects:
        if selected_object_uuids is not None and obje.uuid not in selected_object_uuids:
            continue
        def append_dict(base, new):
            for key, value in new.items():
                if key in base:
                    # merge attributes
                    base[key]['attributes'].extend(value.get('attributes', []))
                else:
                    # add new entry
                    base[key] = value
            return base
        loc = misp_object_helper.create_misp_object(case.id, obje)
        object_uuid_list = append_dict(object_uuid_list, loc)

    if object_uuid_list:
        CaseModel.result_misp_object_module(object_uuid_list, instance_id=instance.id, case_id=case.id)

    if request_form.get("import_standalone_attributes"):
        _import_event_standalone_attributes(
            case,
            event,
            instance.id,
            selected_attribute_uuids=selected_attribute_uuids,
        )

    event_label = f'event {event.id} "{event.info}"'

    if request_form.get("import_event_info_note"):
        _add_markdown_task(
            case,
            "MISP event information",
            f"Metadata of the {event_label}",
            _build_event_info_markdown(event),
            current_user,
        )

    if request_form.get("import_attributes_note"):
        _add_markdown_task(
            case,
            "MISP attributes",
            f"Attributes from {event_label}",
            _build_attributes_markdown(event, selected_attribute_uuids),
            current_user,
        )

    if request_form.get("import_misp_reports"):
        reports = event.to_dict().get("EventReport", [])
        if reports:
            files_dict = {}
            for idx, report in enumerate(reports):
                content = (report.get("content") or "").encode("utf-8")
                name = (report.get("name") or "").strip() or f"event_report_{idx + 1}"
                if not name.lower().endswith(".md"):
                    name = f"{name}.md"
                files_dict[f"report_{idx}"] = FileStorage(
                    stream=BytesIO(content),
                    filename=name,
                    content_type="text/markdown",
                )
            CaseModel.add_file_core(case, files_dict, current_user)

    if request_form.get("import_misp_files"):
        _import_misp_attribute_files(misp, misp_event_id, current_user, case)

    case_connector_instance = Case_Connector_Instance(
        case_id=case.id,
        instance_id=instance.id,
        identifier=misp_event_id,
        is_updating_case=True
    )
    db.session.add(case_connector_instance)
    db.session.commit()

    return case


#################
# Note Template #
#################

def get_note_template(note_id: int):
    """Get a note template model"""
    return Note_Template_Model.query.get(note_id)

def get_all_note_template():
    """Get all note template"""
    return Note_Template_Model.query.all()

def get_note_template_by_page(page: int, title_search: str = None, title_sort: bool = False):
    """Get note template by page"""
    query = Note_Template_Model.query
    if title_search:
        query = query.filter(Note_Template_Model.title.ilike(f"%{title_search}%"))
    if title_sort:
        query = query.order_by(Note_Template_Model.title)
    return query.paginate(page=page, per_page=20, max_per_page=50)

import re

def extract_variables(template_str: str) -> list:
    return list(set(re.findall(r"{{\s*(\w+)\s*}}", template_str)))

def create_note_template(request_json: dict, current_user: int) -> Note_Template_Model:
    """Create a new note template model"""
    content = request_json["content"]
    list_params = extract_variables(content)
    n = Note_Template_Model(
        uuid=str(uuid.uuid4()),
        title=request_json["title"],
        description=request_json.get("description", ""),
        content = content,
        version = 1,
        params={"list": list_params},
        author=current_user.id,
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc)
    )
    db.session.add(n)
    db.session.commit()

    return n


def edit_content_note_template(note_id: int, request_json: dict) -> dict:
    content = request_json["content"]
    list_params = extract_variables(content)
    note_template = get_note_template(note_id)

    content_changed = note_template.content != content
    existing_params = set(note_template.params.get("list", []) if note_template.params else [])
    params_changed = set(list_params) != existing_params

    note_template.content = content
    note_template.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)

    if params_changed:
        note_template.params = {"list": list_params}
    if content_changed or params_changed:
        note_template.version = (note_template.version or 1) + 1

    db.session.commit()
    return {"version": note_template.version or 1}

def edit_note_template(note_id: int, request_json: dict) -> dict:
    note_template = get_note_template(note_id)

    new_title = request_json["title"]
    new_description = request_json["description"]
    changed = (note_template.title != new_title) or (note_template.description != new_description)

    note_template.title = new_title
    note_template.description = new_description
    note_template.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)

    if changed:
        note_template.version = (note_template.version or 1) + 1

    db.session.commit()
    return {"version": note_template.version or 1}

def delete_note_template(note_id: int) -> bool:
    note_template = get_note_template(note_id)
    if not note_template:
        return False
    
    Case_Note_Template_Model.query.filter_by(note_template_id=note_id).delete()
    db.session.delete(note_template)
    db.session.commit()
    return True


#####################
# Search Attr value #
#####################

def search_attr_with_value(attr_value: str, current_user: User, start_date: str = None, end_date: str = None) -> list:
    # Build attribute query with optional filters
    query = Misp_Attribute.query

    # value filter: contains by default (case-insensitive when possible)
    if attr_value:
        pattern = f"%{attr_value}%"
        try:
            query = query.filter(Misp_Attribute.value.ilike(pattern))
        except Exception:
            # fallback for DBs without ilike support
            query = query.filter(Misp_Attribute.value.like(pattern))

    # date filters (creation_date)
    if start_date:
        try:
            dt_start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Misp_Attribute.creation_date >= dt_start)
        except Exception:
            pass
    if end_date:
        try:
            dt_end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            dt_next = dt_end + datetime.timedelta(days=1)
            query = query.filter(Misp_Attribute.creation_date < dt_next)
        except Exception:
            pass

    list_attr = query.all()

    list_case = []
    seen_case_ids = set()

    for attr in list_attr:
        # Determine the case id for this attribute. Attributes can be part of
        # a MISP object (`case_misp_object_id`) or standalone with
        # `case_id` set directly.
        case_id = None
        if attr.case_misp_object_id:
            obj = Case_Misp_Object.query.get(attr.case_misp_object_id)
            if obj:
                case_id = obj.case_id
            else:
                # fallback to attribute's case_id if object record missing
                case_id = attr.case_id
        else:
            case_id = attr.case_id

        if not case_id:
            continue

        if current_user.is_admin():
            case = Case.query.get(case_id)
        else:
            case = Case.query.join(Case_Org, Case_Org.case_id == Case.id)\
            .filter(
                or_(
                    Case_Org.org_id == current_user.org_id,
                    Case.is_private == False
                ),
                Case.id == case_id
            ).first()

        if case and case.id not in seen_case_ids:
            list_case.append(case.to_json())
            seen_case_ids.add(case.id)

    return list_case


#######################
# Community Statistics #
#######################

def get_community_stats():
    """Get community statistics for organisations and users"""
    # Total counts
    total_orgs = Org.query.count()
    total_users = User.query.count()
    active_cutoff = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=30)
    active_users_30d = User.query.filter(User.last_login != None, User.last_login >= active_cutoff).count()
    never_logged_in = User.query.filter(User.last_login == None).count()
    orgs_without_users = db.session.query(Org.id)\
        .outerjoin(User, User.org_id == Org.id)\
        .group_by(Org.id)\
        .having(db.func.count(User.id) == 0)\
        .count()
    
    # Users per organisation
    users_per_org = db.session.query(
        Org.name.label('org_name'),
        db.func.count(User.id).label('count')
    ).join(User, User.org_id == Org.id)\
     .group_by(Org.id, Org.name)\
     .order_by(db.func.count(User.id).desc())\
     .all()
    
    # Users per role
    users_per_role = db.session.query(
        Role.name.label('role_name'),
        db.func.count(User.id).label('count')
    ).join(User, User.role_id == Role.id)\
     .group_by(Role.id, Role.name)\
     .order_by(db.func.count(User.id).desc())\
     .all()
    
    # Open cases per organisation (owner)
    cases_per_org = db.session.query(
        Org.name.label('org_name'),
        db.func.count(Case.id).label('count')
    ).join(Case, Case.owner_org_id == Org.id)\
     .filter(Case.completed == False)\
     .group_by(Org.id, Org.name)\
     .order_by(db.func.count(Case.id).desc())\
     .all()
    
    # Open tasks per user
    tasks_per_user = db.session.query(
        User.first_name,
        User.last_name,
        db.func.count(Task.id).label('count')
    ).join(Task_User, Task_User.user_id == User.id)\
     .join(Task, Task.id == Task_User.task_id)\
     .filter(Task.completed == False)\
     .group_by(User.id, User.first_name, User.last_name)\
     .order_by(db.func.count(Task.id).desc())\
     .all()
    
    return {
        "total_orgs": total_orgs,
        "total_users": total_users,
        "active_users_30d": active_users_30d,
        "never_logged_in": never_logged_in,
        "orgs_without_users": orgs_without_users,
        "avg_users_per_org": round(total_users / total_orgs, 1) if total_orgs else 0,
        "users_per_org": [{"org_name": row.org_name, "count": row.count} for row in users_per_org],
        "users_per_role": [{"role_name": row.role_name, "count": row.count} for row in users_per_role],
        "cases_per_org": [{"org_name": row.org_name, "count": row.count} for row in cases_per_org],
        "tasks_per_user": [{"user_name": f"{row.first_name} {row.last_name}", "count": row.count} for row in tasks_per_user]
    }


############################
# Operational task widgets #
############################

def get_overdue_tasks(current_user, limit=20):
    """Open tasks past their deadline for cases the user can see."""
    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
    cases = Case.query.join(Case_Org, Case_Org.case_id==Case.id)\
        .where(Case_Org.org_id==current_user.org_id).all()
    cases = check_user_in_private_cases(cases, current_user)
    case_ids = [c.id for c in cases]
    if not case_ids:
        return {"count": 0, "tasks": []}

    q = Task.query.filter(Task.case_id.in_(case_ids))\
        .filter(Task.completed == False)\
        .filter(Task.deadline != None)\
        .filter(Task.deadline < now)\
        .order_by(Task.deadline.asc())
    total = q.count()
    rows = q.limit(limit).all()
    return {
        "count": total,
        "tasks": [{
            "id": t.id,
            "case_id": t.case_id,
            "title": t.title,
            "deadline": t.deadline.strftime(DATETIME_FORMAT_FULL),
        } for t in rows],
    }


def get_unassigned_tasks(current_user, limit=20):
    """Open tasks with no assignee for cases the user can see."""
    cases = Case.query.join(Case_Org, Case_Org.case_id==Case.id)\
        .where(Case_Org.org_id==current_user.org_id).all()
    cases = check_user_in_private_cases(cases, current_user)
    case_ids = [c.id for c in cases]
    if not case_ids:
        return {"count": 0, "tasks": []}

    assigned_ids = db.session.query(Task_User.task_id).distinct().subquery()
    q = Task.query.filter(Task.case_id.in_(case_ids))\
        .filter(Task.completed == False)\
        .filter(~Task.id.in_(assigned_ids))\
        .order_by(Task.creation_date.desc())
    total = q.count()
    rows = q.limit(limit).all()
    return {
        "count": total,
        "tasks": [{
            "id": t.id,
            "case_id": t.case_id,
            "title": t.title,
            "creation_date": t.creation_date.strftime(DATETIME_FORMAT_FULL) if t.creation_date else "",
        } for t in rows],
    }


###############
# Admin extra #
###############

def get_admin_extra_stats(days=90):
    """Notification backlog + login activity per day for the last `days` days."""
    notif_backlog = Notification.query.filter_by(is_read=False).count()
    total_notifications = Notification.query.count()

    cutoff = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=days)
    rows = db.session.query(
        db.func.date(Login_Event.login_date).label('day'),
        db.func.count(Login_Event.id).label('count'),
    ).filter(Login_Event.login_date >= cutoff)\
     .group_by('day')\
     .order_by('day')\
     .all()
    activity = [{"calendar": str(r.day), "count": r.count} for r in rows]

    return {
        "notification_backlog": notif_backlog,
        "total_notifications": total_notifications,
        "login_activity": activity,
        "recent_login_count": sum(row["count"] for row in activity),
        "login_activity_days": days,
    }


##################
# Inactive users #
##################

def get_inactive_users(days=90):
    """Users who never logged in or whose last login is older than `days`."""
    cutoff = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=days)
    users = User.query.filter(or_(User.last_login == None, User.last_login < cutoff))\
        .order_by(User.last_login.is_(None).desc(), User.last_login.asc()).all()
    return {
        "days": days,
        "count": len(users),
        "users": [{
            "id": u.id,
            "name": f"{u.first_name} {u.last_name}",
            "email": u.email,
            "last_login": u.last_login.strftime(DATETIME_FORMAT_FULL) if u.last_login else None,
        } for u in users],
    }


def get_recent_logins(limit=20):
    """Most recent login events with user info."""
    rows = db.session.query(Login_Event, User)\
        .join(User, User.id == Login_Event.user_id)\
        .order_by(Login_Event.login_date.desc())\
        .limit(limit).all()
    return {
        "logins": [{
            "user_id": u.id,
            "name": f"{u.first_name} {u.last_name}",
            "email": u.email,
            "login_date": ev.login_date.strftime(DATETIME_FORMAT_FULL) if ev.login_date else None,
        } for ev, u in rows],
    }
