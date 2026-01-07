import json
from .. import db
from ..db_class.db import Configurable_Fields, Misp_Module, Misp_Module_Config, Misp_Module_Result, User
from ..utils.utils import query_get_module
from sqlalchemy import desc
from ..case.CaseCore import CaseModel
from ..case.TaskCore import TaskModel
from ..case import validation_api as CaseModelApi
from ..case import common_core as CommonModel


def get_module(mid):
    """Return a module by id"""
    return Misp_Module.query.get(mid)

def get_module_by_name(name):
    """Return a module by name"""
    return Misp_Module.query.filter_by(name=name).first()

def get_configurable_fields(cid):
    """Return a Configurable_Fields by id"""
    return Configurable_Fields.query.get(cid)

def get_configurable_fields_by_name(name):
    """Return a Configurable_Fields by name"""
    return Configurable_Fields.query.filter_by(name=name).first()

def get_module_config_module(mid, current_user):
    """Return a misp_module_config by module id"""
    return Misp_Module_Config.query.filter_by(module_id=mid, user_id=current_user.id).all()

def get_module_config_both(mid, cid, current_user):
    """Return a misp_module_config by module id and config id"""
    return Misp_Module_Config.query.filter_by(module_id=mid, config_id=cid, user_id=current_user.id).first()

def get_misp_modules_result(mmrid):
    """Return a session by uuid"""
    return Misp_Module_Result.query.filter_by(uuid=mmrid).first()


def util_get_attr(module, loc_list):
    """Additional algo for get_list_misp_attributes"""
    if "input" in module["mispattributes"]:
        for input in module["mispattributes"]["input"]:
            if not input in loc_list:
                loc_list.append(input)
    return loc_list

def get_list_misp_attributes():
    """Return all types of attributes used in expansion and hover"""
    res = query_get_module()
    if not "message" in res:
        loc_list = list()

        for module in res:
            if "expansion" in module["meta"]["module-type"] or "hover" in module["meta"]["module-type"]:
                loc_list = util_get_attr(module, loc_list)
        loc_list.sort()
        return loc_list
    return res

def get_modules():
    """Return all modules for expansion and hover types"""
    res = query_get_module()
    if not "message" in res:
        loc_list = list()
        for module in res:
            module_loc = module
            if ("expansion" in module["meta"]["module-type"] or "hover" in module["meta"]["module-type"]) and module_loc not in loc_list:
                loc_list.append(module_loc)
        loc_list.sort(key=lambda x: x["name"])
        return loc_list
    return res


def get_modules_config(current_user: User):
    """Return configs for all modules """
    modules = Misp_Module.query.order_by(Misp_Module.name).all()
    modules_list = []
    for module in modules:
        loc_module = module.to_json()
        if loc_module["input_attr"]:
            loc_module["input_attr"] = json.loads(loc_module["input_attr"])
        loc_module["config"] = []
        mcs = Misp_Module_Config.query.filter_by(module_id=module.id, user_id=current_user.id).all()
        if not mcs:
            mcs = Misp_Module_Config.query.filter_by(module_id=module.id).where(Misp_Module_Config.user_id == None).all()
        for mc in mcs:
            conf = Configurable_Fields.query.get(mc.config_id)
            loc_module["config"].append({conf.name: mc.value})
        modules_list.append(loc_module)
    return modules_list


def change_config_core(request_json, current_user: User):
    """Change config for a module"""
    module = get_module_by_name(request_json["module_name"])
    for element in request_json:
        if not element == "module_name":
            config = get_configurable_fields_by_name(element)
            if config:
                m_c = get_module_config_both(module.id, config.id, current_user)
                if m_c:
                    m_c.value = request_json[element]
                else:
                    m_c = Misp_Module_Config(
                        module_id=module.id,
                        config_id=config.id,
                        user_id=current_user.id,
                        value=request_json[element]
                    )
                    db.session.add(m_c)
                db.session.commit()
    db.session.commit()
    return True


def get_history(page):
    """Return history"""
    histories = Misp_Module_Result.query.order_by(desc(Misp_Module_Result.id)).paginate(page=page, per_page=20, max_per_page=50)
    return [h.history_json() for h in histories], histories.pages

def get_history_uuid(huuid):
    """Return a history by its uuid"""
    return Misp_Module_Result.query.filter_by(uuid=huuid).first()


def delete_history(huuid, current_user):
    history = get_history_uuid(huuid)
    if history and history.user_id == current_user.id:
        db.session.delete(history)
        db.session.commit()
        return True
    return False

def manage_notes_selected(request_json, current_user):
    case_id = None
    if "create_case" in request_json:
        verif_dict = CaseModelApi.verif_create_case_task(request_json["create_case"])
        if "message" not in verif_dict:
            case = CaseModel.create_case(verif_dict, current_user)
            CaseModel.modify_note_core(case.id, current_user, request_json["notes"])
            case_id = case.id
        else:
            return verif_dict

    if "create_task" in request_json:
        if "case_id" in request_json:
            case_id = request_json["case_id"]
        else:
            return {"message": "No case id passed"}
        
        verif_dict = CaseModelApi.verif_create_case_task(request_json["create_task"])
        if "message" not in verif_dict:
            task = TaskModel.create_task(verif_dict, case_id, current_user)
            TaskModel.modif_note_core(task.id, current_user, request_json["notes"], "-1")
        else:
            return verif_dict

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
        CaseModel.modify_note_core(case_id, current_user, request_json["notes"])

    if "misp-objects" in request_json:
        for misp_obj in request_json["misp-objects"]:
            CaseModel.create_misp_object(case_id, misp_obj, current_user)
    
    return case_id

