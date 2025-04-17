import calendar
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
        
        if task["urls_tools"]:
            for urls_tools in task["urls_tools"]:
                TaskModel.create_url_tool(task_created.id, urls_tools["name"], current_user)

    
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


def chart_dict_constructor(input_dict):
    loc_dict = []
    for elem in input_dict:
        loc_dict.append({
            "calendar": elem,
            "count": input_dict[elem]
        })
    return loc_dict

def stats_core(cases):
    cases_opened_month = {month: 0 for month in calendar.month_name if month}
    cases_opened_year = {}
    cases_closed_month = {month: 0 for month in calendar.month_name if month}
    cases_closed_year = {}
    cases_elapsed_time = {}
    total_opened_cases = 0
    total_closed_cases = 0

    tasks_opened_month = {month: 0 for month in calendar.month_name if month}
    tasks_opened_year = {}
    tasks_closed_month = {month: 0 for month in calendar.month_name if month}
    tasks_closed_year = {}
    tasks_elapsed_time = {}
    tasks_per_case = {}
    total_opened_tasks = 0
    total_closed_tasks = 0

    current_year = datetime.datetime.now().year

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

            total_closed_cases += 1
        else:
            total_opened_cases += 1

        # Tasks part
        for task in case.tasks:
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

                total_closed_tasks += 1
            else:
                total_opened_tasks += 1
            
            if not case.nb_tasks in tasks_per_case:
                tasks_per_case[case.nb_tasks] = 0
            tasks_per_case[case.nb_tasks] += 1


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

    return {"cases-opened-month": loc_cases_opened_month, "cases-opened-year": loc_cases_opened_year,
            "cases-closed-month": loc_cases_closed_month, "cases-closed-year": loc_cases_closed_year,
            "cases-elapsed-time": loc_cases_elapsed_time,
            "total_opened_cases": total_opened_cases, "total_closed_cases": total_closed_cases,
            "tasks-opened-month": loc_tasks_opened_month, "tasks-opened-year": loc_tasks_opened_year,
            "tasks-closed-month": loc_tasks_closed_month, "tasks-closed-year": loc_tasks_closed_year,
            "tasks-elapsed-time": loc_tasks_elapsed_time, "tasks-per-case": loc_tasks_per_case,
            "total_opened_tasks": total_opened_tasks, "total_closed_tasks": total_closed_tasks}


        

    # loc_cases_opened_month = [
    #     {'calendar': 'January', 'count': 25}, {'calendar': 'February', 'count': 5}, {'calendar': 'March', 'count': 10}, 
    #     {'calendar': 'April', 'count': 30}, {'calendar': 'May', 'count': 3}, {'calendar': 'June', 'count': 12}, 
    #     {'calendar': 'July', 'count': 4}, {'calendar': 'August', 'count': 33}, {'calendar': 'September', 'count': 21}, 
    #     {'calendar': 'October', 'count': 55}, {'calendar': 'November', 'count': 7}, {'calendar': 'December', 'count': 70}]
    
    # loc_cases_closed_month = [
    #     {'calendar': 'January', 'count': 11}, {'calendar': 'February', 'count': 6}, {'calendar': 'March', 'count': 1}, 
    #     {'calendar': 'April', 'count': 4}, {'calendar': 'May', 'count': 20}, {'calendar': 'June', 'count': 9}, 
    #     {'calendar': 'July', 'count': 3}, {'calendar': 'August', 'count': 3}, {'calendar': 'September', 'count': 30}, 
    #     {'calendar': 'October', 'count': 50}, {'calendar': 'November', 'count': 6}, {'calendar': 'December', 'count': 3}]
    
    # loc_cases_opened_year = [
    #     {'calendar': '2024', "count": 50}, {'calendar': '2025', "count": 31}
    # ]
    # loc_cases_closed_year = [
    #     {'calendar': '2024', "count": 50}, {'calendar': '2025', "count": 20}
    # ]

    # loc_cases_elapsed_time = [
    #     {"calendar": 1, "count": 30}, {"calendar": 5, "count": 20}, {"calendar": 10, "count": 3}, {"calendar": 24, "count": 2}
    # ]

    # return {"cases-opened-month": loc_cases_opened_month, "cases-opened-year": loc_cases_opened_year,
    #         "cases-closed-month": loc_cases_closed_month, "cases-closed-year": loc_cases_closed_year,
    #         "elapsed-time": loc_cases_elapsed_time}
