import json
import datetime
from .. import db
from ..db_class.db import *
from ..case import case_core as CaseModel
from ..case import task_core as TaskModel
from ..case import case_core_api as CaseModelApi
from ..case import common_core as CommonModel


def get_analyzer(analyzer_id):
    """Return an analyzer by id"""
    return Analyzer.query.get(analyzer_id)

def get_analyzers():
    """Return all Analyzers"""
    return Analyzer.query.all()

def change_status_core(analyzer_id):
    """Active or disabled an analyzer"""
    an = get_analyzer(analyzer_id)
    if an:
        an.is_active = not an.is_active
        db.session.commit()
        return True
    return False

def change_config_core(request_json):
    """Change config for an analyzer"""
    analyzer = get_analyzer(request_json["analyzer_id"])
    if analyzer:
        analyzer.name = request_json["analyzer_name"]
        analyzer.url = request_json["analyzer_url"]
        db.session.commit()
        return True
    return False


def add_analyzer_core(form_dict):
    analyzer = Analyzer(
        name=form_dict["name"],
        url = form_dict["url"],
        is_active=True
    )
    db.session.add(analyzer)
    db.session.commit()
    return True

def delete_analyzer(analyzer_id):
    analyzer = get_analyzer(analyzer_id)
    if analyzer:
        db.session.delete(analyzer)
        return True
    return False


def manage_notes_selected(request_json, current_user, pid):
    case_id = None
    if "create_case" in request_json:
        verif_dict = CaseModelApi.verif_create_case_task(request_json["create_case"], True)
        case = CaseModel.create_case(verif_dict, current_user)
        CaseModel.modif_note_core(case.id, current_user, request_json["notes"])
        case_id = case.id
    if "create_task" in request_json:
        if "case_id" in request_json:
            case_id = request_json["case_id"]
        verif_dict = CaseModelApi.verif_create_case_task(request_json["create_task"], False)
        task = TaskModel.create_task(verif_dict, case_id, current_user)
        TaskModel.modif_note_core(task.id, current_user, request_json["notes"], "-1")
    elif "existing_task_note" in request_json:
        task = CommonModel.get_task(request_json["existing_task_note"]["task_id"])
        TaskModel.modif_note_core(task.id, current_user, request_json["notes"], request_json["existing_task_note"]["note_id"])
        case_id = task.case_id
    elif "create_note" in request_json:
        task = CommonModel.get_task(request_json["create_note"]["task_id"])
        TaskModel.modif_note_core(task.id, current_user, request_json["notes"], "-1")
        case_id = task.case_id
    elif "case_note" in request_json:
        case_id = request_json["case_note"]["case_id"]
        CaseModel.modif_note_core(case_id, current_user, request_json["notes"])

    if "misp-objects" in request_json:
        for misp_obj in request_json["misp-objects"]:
            CaseModel.create_misp_object(case_id, misp_obj)

    # Delete pending
    delete_pending_result(pid)
    return case_id


###########
# Pending #
###########

def get_pending_results(page):
    pending = Analyzer_Result.query.filter_by(is_pending=True).order_by("request_date").paginate(page=page, per_page=25, max_per_page=30)
    return pending

def get_pending_result(pid):
    return Analyzer_Result.query.get(pid)

def add_pending_result(origin_url, pending_result, user):
    p = Analyzer_Result(
        origin_url=origin_url,
        is_pending=True,
        request_date=datetime.datetime.now(tz=datetime.timezone.utc),
        result=json.dumps(pending_result),
        user_id=user.id
    )
    db.session.add(p)
    db.session.commit()
    return True

def get_len_pending_results():
    return Analyzer_Result.query.count()

def delete_pending_result(pid):
    p = get_pending_result(pid)
    if p:
        db.session.delete(p)
        db.session.commit()

def depending_results(pid):
    p = get_pending_result(pid)
    p.is_pending = False
    db.session.commit()