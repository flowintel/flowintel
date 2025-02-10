from ..db_class.db import *
import uuid
import json
import datetime
from ..utils import utils
from ..case.TaskCore import TaskModel
from ..case.CaseCore import CaseModel


def core_read_json_file(case, current_user):
    if not utils.validateCaseJson(case):
        return {"message": f"Case '{case['title']}' format not okay"}
    for task in case["tasks"]:
        if not utils.validateTaskJson(task):
            return {"message": f"Task '{task['title']}' format not okay"}


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
            loc_date = datetime.datetime.strptime(case["deadline"], "%Y-%m-%d %H:%M")
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
                datetime.datetime.strptime(case["recurring_date"], "%Y-%m-%d %H:%M")
            except:
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
    for tag in case["tags"]:
        if not utils.check_tag(tag):
            return {"message": f"Case '{case['title']}': tag '{tag}' doesn't exist"}
    
    # Clusters
    for i in range(0, len(case["clusters"])):
        case["clusters"][i] = case["clusters"][i]["name"]

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
                loc_date = datetime.datetime.strptime(task["deadline"], "%Y-%m-%d %H:%M")
                task["deadline_date"] = loc_date.date()
                task["deadline_time"] = loc_date.time()
            except:
                return {"message": f"Task '{task['title']}': deadline bad format, %Y-%m-%d %H:%M"}
        else:
            task["deadline_date"] = ""
            task["deadline_time"] = ""

        for tag in task["tags"]:
            if not utils.check_tag(tag):
                return {"message": f"Task '{task['title']}': tag '{tag}' doesn't exist"}
            
        # Clusters
        for i in range(0, len(task["clusters"])):
            task["clusters"][i] = task["clusters"][i]["name"]
        
        task["custom_tags"] = []

    #################
    ## DB Creation ##
    ################

    ## Case creation
    case_created = CaseModel.create_case(case, current_user)
    if case["notes"]:
        CaseModel.modif_note_core(case_created.id, current_user, case["notes"])

    ## Task creation
    for task in case["tasks"]:
        task_created = TaskModel.create_task(task, case_created.id, current_user)
        if task["notes"]:
            for note in task["notes"]:
                loc_note = TaskModel.create_note(task_created.id, current_user)
                TaskModel.modif_note_core(task_created.id, current_user, note["note"], loc_note.id)
        
        if task["subtasks"]:
            for subtask in task["subtasks"]:
                TaskModel.create_subtask(task_created.id, subtask["description"], current_user)

    
def read_json_file(files_list, current_user):
    for file in files_list:
        if files_list[file].filename:
            try:
                file_data = json.loads(files_list[file].read().decode())
                if type(file_data) == list:
                    for case in file_data:
                        res = core_read_json_file(case, current_user)
                        if res: return res
                else:
                    return core_read_json_file(file_data, current_user)
            except Exception as e:
                print(e)
                return {"message": "Something went wrong"}
