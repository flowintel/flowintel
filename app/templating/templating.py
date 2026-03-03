import ast
import datetime
import hashlib
import json
import os
from flask import Blueprint, render_template, redirect, jsonify, request, flash, current_app
from flask_login import login_required, current_user
from .TemplateCase import TemplateModel
from . import common_template_core as CommonModel
from .TaskTemplateCore import TaskModel
from ..decorators import editor_required, template_editor_required
from .form import TaskTemplateForm, CaseTemplateForm, TaskTemplateEditForm, CaseTemplateEditForm
from ..utils.utils import form_to_dict
from ..utils.formHelper import prepare_tags
from ..case import common_core as CommonCaseModel
from ..case.common_core import get_instance_with_icon
from ..utils.logger import flowintel_log
from ..db_class.db import Template_Repository, Template_Repository_Entry, Case_Template, Task_Template, Case_Task_Template
from .. import db

templating_blueprint = Blueprint(
    'templating',
    __name__,
    template_folder='templates',
    static_folder='static'
)


##########
# Render #
##########

@templating_blueprint.route("/cases", methods=['GET'])
@login_required
def case_templates_index():
    """View all case templates"""
    return render_template("templating/case_templates_index.html")

@templating_blueprint.route("/tasks", methods=['GET', "POST"])
@login_required
def task_template_view():
    """View all task templates"""
    return render_template("templating/task_template.html")


@templating_blueprint.route("/create_case", methods=['GET','POST'])
@login_required
@template_editor_required
def create_case_template():
    """Create a case Template"""
    form = CaseTemplateForm()

    task_template_query_list = CommonModel.get_all_task_templates()
    form.tasks.choices = [(template.id, template.title) for template in task_template_query_list]
    
    if form.validate_on_submit():
        res = prepare_tags(request)
        if isinstance(res, dict):
            form_dict = form_to_dict(form)
            form_dict.update(res)
            form_dict["description"] = request.form.get("description")
            template = TemplateModel.create_case(form_dict)
            flowintel_log("audit", 201, "Case template created", User=current_user.email, TemplateId=template.id, Title=template.title)
            flash("Template created", "success")
            return redirect(f"/templating/case/{template.id}")
        return render_template("templating/create_case_template.html", form=form)
    return render_template("templating/create_case_template.html", form=form)


@templating_blueprint.route("/create_task", methods=['GET','POST'])
@login_required
@template_editor_required
def create_task_template():
    """Create a task Template"""
    form = TaskTemplateForm()
    form.tasks.choices = [(template.id, template.title) for template in  CommonModel.get_all_task_templates()]
    if form.validate_on_submit():
        res = prepare_tags(request)
        if isinstance(res, dict):
            form_dict = form_to_dict(form)
            form_dict.update(res)
            form_dict["description"] = request.form.get("description")
            template = TaskModel.add_task_template_core(form_dict)
            flowintel_log("audit", 201, "Task template created", User=current_user.email, TemplateId=template.id, Title=template.title)
            flash("Template created", "success")
            return redirect(f"/templating/tasks")
        return render_template("templating/create_task_template.html", form=form)
    return render_template("templating/create_task_template.html", form=form)


@templating_blueprint.route("/case/<cid>", methods=['GET','POST'])
@login_required
def case_template_view(cid):
    """View a case Template"""
    template = CommonModel.get_case_template(cid)
    if template:
        return render_template("templating/case_template_view.html", case_id=cid)
    return render_template("404.html")

@templating_blueprint.route("/get_case_template/<cid>", methods=['GET'])
@login_required
def get_case_template(cid):
    """View a case Template"""
    template = CommonModel.get_case_template(cid)
    return {"template": template.to_json()}

@templating_blueprint.route("/case/<cid>/add_task", methods=['GET','POST'])
@login_required
@template_editor_required
def add_task_case(cid):
    """Add a task Template"""
    form = TaskTemplateForm()
    task_template_query_list = CommonModel.get_all_task_templates()
    task_by_case = CommonModel.get_task_by_case(cid)
    task_id_list = [tid.id for tid in task_by_case]
    form.tasks.choices = [(template.id, template.title) for template in task_template_query_list if template.id not in task_id_list]
    if form.validate_on_submit():
        res = prepare_tags(request)
        if isinstance(res, dict):
            form_dict = form_to_dict(form)
            form_dict.update(res)
            form_dict["description"] = request.form.get("description")
            TemplateModel.add_task_case_template(form_dict, cid)
            flash("Template added", "success")
            return redirect(f"/templating/case/{cid}")
        return render_template("templating/add_task_case.html", form=form)
    return render_template("templating/add_task_case.html", form=form)


@templating_blueprint.route("/edit_case/<cid>", methods=['GET','POST'])
@login_required
@template_editor_required
def edit_case(cid):
    """Edit a case Template"""
    template = CommonModel.get_case_template(cid)
    if template:
        form = CaseTemplateEditForm()
        form.template_id.data = cid
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            form_dict["description"] = request.form.get("description")
            TemplateModel.edit(form_dict, cid)
            flowintel_log("audit", 200, "Case template edited", User=current_user.email, TemplateId=cid, Title=form_dict.get("title"))
            flash("Template edited", "success")
            return redirect(f"/templating/case/{cid}")
        else:
            form.title.data = template.title
            form.time_required.data = template.time_required

        return render_template("templating/edit_case_template.html", form=form, description=template.description)
    return render_template("404.html")

@templating_blueprint.route("/case/edit_tags/<cid>", methods=['GET','POST'])
@login_required
@template_editor_required
def edit_case_tags(cid):
    """Edit the case"""
    if CommonModel.get_case_template(cid):
        tag_list = request.json["tags_select"]
        cluster_list = request.json["clusters_select"]
        custom_tags_list = request.json["custom_select"]
        if isinstance(CommonCaseModel.check_tag(tag_list), bool):
            if isinstance(CommonCaseModel.check_cluster(cluster_list), bool):
                loc_dict = {
                    "tags": tag_list,
                    "clusters": cluster_list,
                    "custom_tags": custom_tags_list
                }
                TemplateModel.edit_tags(loc_dict, cid)
                flowintel_log("audit", 200, "Case template tags edited", User=current_user.email, TemplateId=cid)
                return {"message": "Tags edited", "toast_class": "success-subtle"}, 200
            return {"message": "Error with Clusters", "toast_class": "warning-subtle"}, 400
        return {"message": "Error with Tags", "toast_class": "warning-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/edit_task/<tid>", methods=['GET','POST'])
@login_required
@template_editor_required
def edit_task(tid):
    """Edit a task Template"""
    template = CommonModel.get_task_template(tid)
    case_id = request.args.get('case_id')
    if template:
        form = TaskTemplateEditForm()
        form.template_id.data = tid
        if form.validate_on_submit():
            res = prepare_tags(request)
            if isinstance(res, dict):
                form_dict = form_to_dict(form)
                form_dict.update(res)
                form_dict["description"] = request.form.get("description")
                TaskModel.edit_task_template(form_dict, tid)
                flowintel_log("audit", 200, "Task template edited", User=current_user.email, TemplateId=tid, Title=form_dict.get("title"))
                flash("Template edited", "success")
                if case_id:
                    return redirect(f"/templating/case/{case_id}")
                return redirect(f"/templating/tasks")
            return render_template("templating/edit_task_template.html", form=form, description=template.description, case_id=case_id)
        else:
            form.title.data = template.title
            form.time_required.data = template.time_required

        return render_template("templating/edit_task_template.html", form=form, description=template.description, case_id=case_id)
    return render_template("404.html")


@templating_blueprint.route("/get_all_case_templates", methods=['GET'])
@login_required
def get_all_case_templates():
    """Get all case templates"""
    templates = CommonModel.get_all_case_templates()
    templates_list = list()
    for template in templates:
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        templates_list.append(loc_template)
    return {"templates": templates_list}


@templating_blueprint.route("/get_page_case_templates", methods=['GET'])
@login_required
def get_page_case_templates():
    """Get a page of case templates"""
    page = request.args.get('page', 1, type=int)
    title_filter = request.args.get('title')
    q = request.args.get('q', None, type=str)
    tags = request.args.get('tags')
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    custom_tags = request.args.get('custom_tags')

    if tags:
        tags = ast.literal_eval(tags)
    if taxonomies:
        taxonomies = ast.literal_eval(taxonomies)

    if galaxies:
        galaxies = ast.literal_eval(galaxies)
    if clusters:
        clusters = ast.literal_eval(clusters)

    if custom_tags:
        custom_tags = ast.literal_eval(custom_tags)

    templates, nb_pages = TemplateModel.sort_cases(page, 
                                        title_filter, 
                                        taxonomies,
                                        galaxies, 
                                        tags, 
                                        clusters, 
                                        custom_tags,
                                        or_and_taxo, 
                                        or_and_galaxies,
                                        q)

    templates_list = list()
    for template in templates:
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        templates_list.append(loc_template)
    return {"templates": templates_list, "nb_pages": nb_pages}


@templating_blueprint.route("/get_case_template/<cid>", methods=['GET'])
@login_required
def get_template(cid):
    """Get a case template"""
    template = CommonModel.get_case_template(cid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}



##############
# Connectors #
##############

@templating_blueprint.route("/<tid>/get_case_template_connector_instances", methods=['GET'])
@login_required
def get_case_template_connector_instances(tid):
    connector_instances = CommonModel.get_case_template_connector_instances(tid)
    if connector_instances:
        c_i_formated = list()
        for c_i in connector_instances:
            c_i_formated.append({
                **c_i.to_json(),
                "details": get_instance_with_icon(c_i.connector_instance_id),
                "template_instance_id": c_i.id,
                })
        return {"connector_instances": c_i_formated}, 200
    return {"connector_instances": connector_instances}, 200


@templating_blueprint.route("/<tid>/add_connector", methods=['POST'])
@login_required
@template_editor_required
def add_connector(tid):
    """Add connector instance to template"""
    if CommonModel.get_case_template(tid):
        if "connector_instances" in request.json and CommonModel.add_connector_instances_to_case_template(tid, request.json['connector_instances']):
            return {"message": "Connector added successfully", "toast_class": "success-subtle"}, 200
        return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@templating_blueprint.route("/connectors/<ctid>/remove_connector", methods=['GET'])
@login_required
@template_editor_required
def remove_connector(ctid):
    """Remove connector instance from template"""
    if CommonModel.remove_connector_instance_from_case_template(ctid):
        return {"message": "Connector removed", 'toast_class': "success-subtle"}, 200
    return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403


@templating_blueprint.route("/connectors/<ctid>/edit_connector", methods=['POST'])
@login_required
@template_editor_required
def edit_connector(ctid):
    """Edit connector instance of template"""
    if "identifier" in request.json:
        if CommonModel.edit_connector_instances_of_case_template(ctid, request.json["identifier"]):
            return {"message": "Connector edited successfully", "toast_class": "success-subtle"}, 200
        return {"message": "Error editing connector", "toast_class": "danger-subtle"}, 400
    return {"message": "Need to pass 'connectors'", "toast_class": "warning-subtle"}, 400


##########
## Task ##
##########

@templating_blueprint.route("/get_task_template/<tid>", methods=['GET'])
@login_required
def get_task_template(tid):
    """Get a task template"""
    template = CommonModel.get_task_template(tid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@templating_blueprint.route("/get_all_task_templates", methods=['GET'])
@login_required
def get_all_task_templates():
    """Get all task templates"""
    templates = CommonModel.get_all_task_templates()
    templates_list = list()
    for template in templates:
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        templates_list.append(loc_template)
    return {"templates": templates_list}


@templating_blueprint.route("/get_page_task_templates", methods=['GET'])
@login_required
def get_page_task_templates():
    """Get a page of task template"""
    page = request.args.get('page', 1, type=int)
    title_filter = request.args.get('title')
    tags = request.args.get('tags')
    q = request.args.get('q', None, type=str)
    
    taxonomies = request.args.get('taxonomies')
    or_and_taxo = request.args.get("or_and_taxo")

    galaxies = request.args.get('galaxies')
    clusters = request.args.get('clusters')
    or_and_galaxies = request.args.get("or_and_galaxies")

    custom_tags = request.args.get('custom_tags')

    if tags:
        tags = ast.literal_eval(tags)
    if taxonomies:
        taxonomies = ast.literal_eval(taxonomies)

    if galaxies:
        galaxies = ast.literal_eval(galaxies)
    if clusters:
        clusters = ast.literal_eval(clusters)

    if custom_tags:
        custom_tags = ast.literal_eval(custom_tags)

    templates, nb_pages = TaskModel.sort_tasks(page, 
                                                title_filter, 
                                                taxonomies, 
                                                galaxies, 
                                                tags, 
                                                clusters,
                                                custom_tags,
                                                or_and_taxo, 
                                                or_and_galaxies,
                                                q)

    if templates:
        templates_list = list()
        for template in templates:
            templates_list.append(TemplateModel.regroup_task_info(template, current_user))
        return {"templates": templates_list, "nb_pages": nb_pages}
    return {"message": "Template not found"}


@templating_blueprint.route("/get_task_by_case/<cid>", methods=['GET'])
@login_required
def get_task_by_case(cid):
    """Get a task template by a case template"""
    templates = CommonModel.get_task_by_case(cid)
    if templates:
        templates_list = list()
        for template in templates:
            loc_template = TemplateModel.regroup_task_info(template, current_user)
            loc_template["case_order_id"] = CommonModel.get_task_by_case_class(cid, template.id).case_order_id
            templates_list.append(loc_template)
        return {"tasks": templates_list}
    return {"tasks": []}


@templating_blueprint.route("/case/<cid>/remove_task/<tid>", methods=['GET'])
@login_required
@template_editor_required
def remove_task(cid, tid):
    """Remove a task template form a case template"""
    if CommonModel.get_task_template(tid):
        if TemplateModel.remove_task_case(cid, tid):
            return {"message":"Task Template removed", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template removed", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/delete_task/<tid>", methods=['GET'])
@login_required
@template_editor_required
def delete_task(tid):
    """Delete a task template"""
    template = CommonModel.get_task_template(tid)
    if template:
        if TaskModel.delete_task_template(tid):
            flowintel_log("audit", 200, "Task template deleted", User=current_user.email, TemplateId=tid, TemplateTitle=template.title)
            return {"message":"Task Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/delete_case/<cid>", methods=['GET'])
@login_required
@template_editor_required
def delete_case(cid):
    """Delete a case template"""
    template = CommonModel.get_case_template(cid)
    if template:
        if TemplateModel.delete_case(cid):
            flowintel_log("audit", 200, "Case template deleted", User=current_user.email, TemplateId=cid, Title=template.title)
            return {"message":"Case Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Case Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/create_case_from_template/<cid>", methods=['POST'])
@login_required
@editor_required
def create_case_from_template(cid):
    """Create a case from a template"""
    template = CommonModel.get_case_template(cid)
    if template:
        case_title_fork = request.json["case_title_fork"]
        new_case = TemplateModel.create_case_from_template(cid, case_title_fork, current_user)
        if type(new_case) == dict:
            return new_case
        flowintel_log("audit", 200, "Case created from template", User=current_user.email, TemplateId=cid, CaseId=new_case.id, CaseTitle=new_case.title)
        return {"new_case_id": new_case.id}, 201
    return {"message": "Template not found"}


@templating_blueprint.route("/case/<cid>/download", methods=['GET'])
@login_required
@editor_required
def download_case(cid):
    """Download a case template"""
    case = CommonModel.get_case_template(cid)
    task_list = [task.download() for task in CommonModel.get_task_by_case(cid)]
    return_dict = case.download()
    return_dict["tasks_template"] = task_list
    return jsonify(return_dict), 200, {'Content-Disposition': f'attachment; filename=template_case_{case.title}.json'}

@templating_blueprint.route("/case/<cid>/modif_note_case", methods=['POST'])
@login_required
@template_editor_required
def modif_note_case(cid):
    """Modify note of the task"""
    if CommonModel.get_case_template(cid):
        notes = request.json["notes"]
        if TemplateModel.modif_note_core(cid, notes):
            flowintel_log("audit", 200, "Case template note modified", User=current_user.email, TemplateId=cid, NoteLength=len(notes) if notes else 0)
            return {"message": "Notes modified", "toast_class": "success-subtle"}, 200
        return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/task/<tid>/create_note", methods=['GET'])
@login_required
@template_editor_required
def task_create_note(tid):
    """Create a new note for the template"""
    res_note = TaskModel.create_note(tid)
    if res_note:
        return {"note": res_note.to_json(), "message": "Note created", "toast_class": "success-subtle"}, 200
    return {"message": "Error create note", "toast_class": "danger-subtle"}, 400

@templating_blueprint.route("/task/<tid>/delete_note", methods=['GET'])
@login_required
@template_editor_required
def task_delete_note(tid):
    """Create a new note for the template"""
    if CommonModel.get_task_template(tid):
        if "note_id" in request.args:
            if TaskModel.delete_note(tid, request.args.get("note_id")):
                return {"message": "Note deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Error delete note", "toast_class": "danger-subtle"}, 400
        return {"message": "Need to pass a note id", "toast_class": "warning-subtle"}, 400
    return {"message": "Task not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/task/<tid>/get_note", methods=['GET'])
@login_required
def task_get_note(tid):
    """Get not of a task in text format"""
    task = CommonModel.get_task_template(tid)
    if task:
        if "note_id" in request.args:
            task_note = CommonModel.get_task_note(request.args.get("note_id"))
            return {"notes": task_note.note}, 200
        return {"message": "Need to pass a note id", "toast_class": "warning-subtle"}, 400
    return {"message": "Task not found", "toast_class": "danger-subtle"}, 404

@templating_blueprint.route("/task/<tid>/modif_note", methods=['POST'])
@login_required
@template_editor_required
def task_modif_note(tid):
    """Modify note of the task"""
    if CommonModel.get_task_template(tid):
        notes = request.json["notes"]
        if "note_id" in request.args:
            res_note = TaskModel.modif_note_core(tid, notes, request.args.get("note_id"))
            if res_note:
                flowintel_log("audit", 200, "Task template note modified", User=current_user.email, TemplateId=tid, NoteId=request.args.get("note_id"))
                return {"note": res_note.to_json(), "message": "Note added", "toast_class": "success-subtle"}, 200
            return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
        return {"message": "Need to pass a note id", "toast_class": "warning-subtle"}, 400
    return {"message": "Task not found", "toast_class": "danger-subtle"}, 404
    

@templating_blueprint.route("/get_taxonomies_case/<cid>", methods=['GET'])
@login_required
def get_taxonomies_case(cid):
    if CommonModel.get_case_template(cid):
        tags = CommonModel.get_case_template_tags_json(cid)
        taxonomies = CommonModel.get_taxonomies_from_tags(tags)
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/get_taxonomies_task/<tid>", methods=['GET'])
@login_required
def get_taxonomies_task(tid):
    if CommonModel.get_task_template(tid):
        tags = CommonModel.get_task_template_tags_json(tid)
        taxonomies = CommonModel.get_taxonomies_from_tags(tags)
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


@templating_blueprint.route("/get_galaxies_case/<cid>", methods=['GET'])
@login_required
def get_galaxies_case(cid):
    if CommonModel.get_case_template(cid):
        clusters = CommonModel.get_case_clusters(cid)
        clusters, galaxies = CommonModel.get_galaxies_from_clusters(clusters)
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/get_galaxies_task/<tid>", methods=['GET'])
@login_required
def get_galaxies_task(tid):
    if CommonModel.get_task_template(tid):
        clusters = CommonModel.get_task_clusters(tid)
        clusters, galaxies = CommonModel.get_galaxies_from_clusters(clusters)

        # Galaxy without cluster
        loc_galax = CommonModel.get_task_galaxies(tid)
        for loc_g in loc_galax:
            if not loc_g.to_json() in galaxies:
                galaxies.append(loc_g.to_json())
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


@templating_blueprint.route("/case/<cid>/change_order/<tid>", methods=['GET', 'POST'])
@login_required
@template_editor_required
def change_order(cid, tid):
    """Change the order of tasks"""
    case = CommonModel.get_case_template(cid)
    if case:
        task = CommonModel.get_task_template(tid)
        if task:
            if TaskModel.change_order(case, task, request.json):
                return {"message": "Order changed", 'toast_class': "success-subtle"}, 200
            return {"message": "New index is not one of an other task", 'toast_class': "success-subtle"}, 200
        return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@templating_blueprint.route("/get_custom_tags_case/<cid>", methods=['GET'])
@login_required
def get_custom_tags_case(cid):
    """Get all custom tags for a case template"""
    case = CommonModel.get_case_template(cid)
    if case:
        return {"custom_tags": CommonModel.get_case_custom_tags_json(case.id)}, 200
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/get_custom_tags_task/<cid>", methods=['GET'])
@login_required
def get_custom_tags_task(cid):
    """Get all custom tags for a task template"""
    task = CommonModel.get_task_template(cid)
    if task:
        return {"custom_tags": CommonModel.get_task_custom_tags_json(task.id)}, 200
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


############
# Subtasks #
############

@templating_blueprint.route("/task/<tid>/create_subtask", methods=['POST'])
@login_required
@template_editor_required
def create_subtask(tid):
    """Create a subtask for a task template"""
    task = CommonModel.get_task_template(tid)
    if task:
        if "description" in request.json:
            description = request.json["description"]
            subtask = TaskModel.create_subtask(tid, description)
            if subtask:
                return {"message": f"Subtask created, id: {subtask.id}", 'toast_class': "success-subtle"}, 200 
            return {"message": "Error creating subtask", 'toast_class': "danger-subtle"}, 400
        return {"message": "Need to pass 'description", 'toast_class': "warning-subtle"}, 400
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/task/<tid>/edit_subtask/<sid>", methods=['POST'])
@login_required
@template_editor_required
def edit_subtask(tid, sid):
    """Edit a subtask of a task template"""
    task = CommonModel.get_task_template(tid)
    if task:
        if "description" in request.json:
            description = request.json["description"]
            if TaskModel.edit_subtask(tid, sid, description):
                return {"message": "Subtask edited", 'toast_class': "success-subtle"}, 200 
            return {"message": "Subtask not found", 'toast_class': "danger-subtle"}, 404
        return {"message": "Need to pass 'description", 'toast_class': "warning-subtle"}, 400
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/task/<tid>/delete_subtask/<sid>", methods=['GET'])
@login_required
@template_editor_required
def delete_subtask(tid, sid):
    """Delete a subtask of a task template"""
    task = CommonModel.get_task_template(tid)
    if task:
        if TaskModel.delete_subtask(tid, sid):
            return {"message": "Subtask deleted", 'toast_class': "success-subtle"}, 200 
        return {"message": "Subtask not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404



##############
# Urls/Tools #
##############


@templating_blueprint.route("/task/<tid>/create_url_tool", methods=['POST'])
@login_required
@template_editor_required
def create_url_tool(tid):
    """Create a new Url/Tool"""
    task = CommonModel.get_task_template(tid)
    if task:
        if "name" in request.json:
            url_tool = TaskModel.create_url_tool(tid, request.json["name"])
            if url_tool:
                return {"message": f"Url/Tool created", "id": url_tool.id, 'toast_class': "success-subtle", "icon": "fas fa-plus"}, 200 
            return {"message": "Error creating Url/Tool", 'toast_class': "danger-subtle"}, 400
        return {"message": "Need to pass 'name", 'toast_class': "warning-subtle"}, 400
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/task/<tid>/edit_url_tool/<utid>", methods=['POST'])
@login_required
@template_editor_required
def edit_url_tool(tid, utid):
    """Edit a Url/Tool"""
    task = CommonModel.get_task_template(tid)
    if task:
        if "name" in request.json:
            if TaskModel.edit_url_tool(tid, utid, request.json["name"]):
                return {"message": "Url/Tool edited", 'toast_class': "success-subtle"}, 200 
            return {"message": "Url/Tool not found", 'toast_class': "danger-subtle"}, 404
        return {"message": "Need to pass 'name", 'toast_class': "warning-subtle"}, 400
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404

@templating_blueprint.route("/task/<tid>/delete_url_tool/<utid>", methods=['GET'])
@login_required
@template_editor_required
def delete_url_tool(tid, utid):
    """Delete a Url/Tool"""
    task = CommonModel.get_task_template(tid)
    if task:
        if TaskModel.delete_url_tool(tid, utid):
            return {"message": "Url/Tool deleted", 'toast_class': "success-subtle", "icon": "fas fa-trash"}, 200 
        return {"message": "Url/Tool not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


##########
# Repositories
##########

@templating_blueprint.route("/repositories/<int:rid>/check", methods=['GET'])
@login_required
@template_editor_required
def repository_check(rid):
    """Verify the local cloned repository exists and contains a valid manifest.json."""
    repo = Template_Repository.query.get(rid)
    if not repo:
        return {"message": "Repository not found", "toast_class": "danger-subtle"}, 404

    if not repo.local_path:
        return {"reachable": False, "error": "No local path configured for this repository"}, 200

    base = _repo_base_path(repo.local_path)
    if not os.path.isdir(base):
        flowintel_log("audit", 200, "Template repository check — path not found",
                      User=current_user.email, RepositoryId=repo.id, Name=repo.name, Path=repo.local_path)
        return {"reachable": False, "error": f"Directory not found: {repo.local_path}"}, 200

    manifest_path = os.path.join(base, "manifest.json")
    if not os.path.isfile(manifest_path):
        return {"reachable": True, "valid": False, "error": "manifest.json not found in the repository"}, 200

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as exc:
        return {"reachable": True, "valid": False, "error": f"manifest.json is not valid JSON: {exc}"}, 200

    required_keys = {"name", "description", "uuid", "version"}
    missing = required_keys - set(manifest.keys())
    valid = not missing
    flowintel_log("audit", 200, "Template repository check",
                  User=current_user.email, RepositoryId=repo.id, Name=repo.name, Valid=valid)
    return {
        "reachable": True, "valid": valid, "missing_keys": sorted(missing),
        "manifest": manifest, "local_path": repo.local_path,
        "local_version": repo.version, "manifest_version": manifest.get("version"),
    }, 200


@templating_blueprint.route("/repositories/<int:rid>/refresh", methods=['POST'])
@login_required
@template_editor_required
def repository_refresh(rid):
    repo = Template_Repository.query.get(rid)
    if not repo:
        return {"message": "Repository not found", "toast_class": "danger-subtle"}, 404

    if not repo.local_path:
        return {"message": "No local path configured for this repository", "toast_class": "warning-subtle"}, 200

    base = _repo_base_path(repo.local_path)
    manifest_path = os.path.join(base, "manifest.json")
    if not os.path.isfile(manifest_path):
        flowintel_log("audit", 200, "Template repository refresh failed — manifest.json not found",
                      User=current_user.email, RepositoryId=repo.id, Name=repo.name, Path=repo.local_path)
        return {"message": f"manifest.json not found at: {repo.local_path}", "toast_class": "danger-subtle"}, 200

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as exc:
        flowintel_log("audit", 200, "Template repository refresh failed — invalid manifest",
                      User=current_user.email, RepositoryId=repo.id, Name=repo.name, Error=str(exc))
        return {"message": f"Could not read manifest.json: {exc}", "toast_class": "danger-subtle"}, 200

    required_keys = {"name", "description", "uuid", "version"}
    missing = required_keys - set(manifest.keys())
    if missing:
        flowintel_log("audit", 200, "Template repository refresh failed — invalid manifest",
                      User=current_user.email, RepositoryId=repo.id, Name=repo.name, MissingKeys=sorted(missing))
        return {"message": f"manifest.json is missing required fields: {', '.join(sorted(missing))}", "toast_class": "warning-subtle"}, 200

    new_name = (manifest["name"] or "").strip() or repo.name
    new_description = (manifest["description"] or "").strip() or None
    new_version = manifest.get("version")

    field_changes = []
    if new_name != repo.name:
        field_changes.append(f'name: "{repo.name}" → "{new_name}"')
        repo.name = new_name
    if new_description != repo.description:
        old_desc = repo.description or "(none)"
        new_desc = new_description or "(none)"
        field_changes.append(f'description: "{old_desc}" → "{new_desc}"')
        repo.description = new_description
    if new_version != repo.version:
        field_changes.append(f'version: {repo.version} → {new_version}')
        repo.version = new_version

    if field_changes:
        db.session.commit()

    entries_list, scan_error = _scan_local_entries(repo)
    case_count = sum(1 for e in entries_list if e["type"] == "case")
    task_count = sum(1 for e in entries_list if e["type"] == "task")
    scan_note = f" — {case_count} case, {task_count} task template(s) found" if entries_list else ""
    if scan_error:
        scan_note = f" (scan error: {scan_error})"

    if not field_changes:
        flowintel_log("audit", 200, "Template repository refresh — already up to date",
                      User=current_user.email, RepositoryId=repo.id, Name=repo.name)
        return {"message": f"'{repo.name}' is already up to date{scan_note}", "toast_class": "success-subtle",
                "repository": repo.to_json(),
                "entries": _annotate_local_grouped(entries_list),
                }, 200

    change_summary = ", ".join(field_changes)
    flowintel_log("audit", 200, "Template repository refreshed",
                  User=current_user.email, RepositoryId=repo.id, Name=repo.name, Changes=change_summary)
    return {"message": f"'{repo.name}' updated — {change_summary}{scan_note}", "toast_class": "success-subtle",
            "repository": repo.to_json(),
            "entries": _annotate_local_grouped(entries_list),
            }, 200



# ── Remote template scanning helpers ────────────────────────────────────────

def _annotate_local(entries_list):
    """
    Enriches each entry dict with local copy information:
      local        – True if a matching UUID exists locally
      localVersion – the local template's version (or None)
      localNewer   – True when the local copy is ahead of the remote
    """
    case_uuids = {e["uuid"] for e in entries_list if e.get("type") == "case"}
    task_uuids = {e["uuid"] for e in entries_list if e.get("type") == "task"}

    local_cases = {}
    if case_uuids:
        for ct in Case_Template.query.filter(Case_Template.uuid.in_(case_uuids)).all():
            local_cases[ct.uuid] = ct.version or 1

    local_tasks = {}
    if task_uuids:
        for tt in Task_Template.query.filter(Task_Template.uuid.in_(task_uuids)).all():
            local_tasks[tt.uuid] = tt.version or 1

    for entry in entries_list:
        t = entry.get("type")
        uuid = entry.get("uuid", "")
        local_ver = local_cases.get(uuid) if t == "case" else local_tasks.get(uuid) if t == "task" else None
        entry["local"] = local_ver is not None
        entry["localVersion"] = local_ver
        entry["localNewer"] = bool(local_ver and entry.get("version") and local_ver > entry["version"])
    return entries_list


def _annotate_local_grouped(entries_list):
    """Annotate and return entries split into {case: [...], task: [...]} dict."""
    annotated = _annotate_local(entries_list)
    return {
        "case": [e for e in annotated if e["type"] == "case"],
        "task": [e for e in annotated if e["type"] == "task"],
    }




def _repo_base_path(local_path):
    """Resolve a repository's local_path to an absolute filesystem path.

    Relative paths are resolved from the project root (parent of the Flask app package).
    """
    if os.path.isabs(local_path):
        return local_path
    project_root = os.path.dirname(current_app.root_path)
    return os.path.normpath(os.path.join(project_root, local_path))


def _read_entry_file(repo, entry):
    """Read and parse the JSON template file for a given entry from the local cloned repo.

    Returns (data_dict, None) on success, or (None, error_message) on failure.
    """
    if not entry.download_url:
        return None, "No file path recorded for this entry"
    if not repo or not repo.local_path:
        return None, "Repository has no local path configured"
    base = _repo_base_path(repo.local_path)
    filepath = os.path.normpath(os.path.join(base, entry.download_url))
    # Guard against path traversal
    if not filepath.startswith(base + os.sep) and filepath != base:
        return None, "Invalid file path"
    if not os.path.isfile(filepath):
        return None, f"File not found: {entry.download_url}"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return None, f"Could not read template file: {exc}"


def _scan_local_entries(repo):
    """Scan the local cloned repository for case/ and task/ template files.

    Walks case/ and task/ subdirectories, parses each .json file, and upserts
    the corresponding Template_Repository_Entry rows.
    Returns (entries_json_list, error_string_or_None).
    """
    if not repo.local_path:
        return [], "No local path configured for this repository"
    base = _repo_base_path(repo.local_path)
    if not os.path.isdir(base):
        return [], f"Local path not found: {repo.local_path}"

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    upserted = []

    for tpl_type in ("case", "task"):
        type_dir = os.path.join(base, tpl_type)
        if not os.path.isdir(type_dir):
            continue

        for filename in sorted(os.listdir(type_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(type_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tpl = json.load(f)
            except Exception:
                continue

            uuid_ = tpl.get("uuid", "")
            if not uuid_:
                continue

            title_ = (tpl.get("title") or tpl.get("name") or filename.replace(".json", "")).strip()
            description_ = (tpl.get("description") or "")[:500]
            version_ = tpl.get("version")
            relative_path = f"{tpl_type}/{filename}"

            with open(filepath, "rb") as f:
                file_sha = hashlib.sha1(f.read()).hexdigest()

            entry = Template_Repository_Entry.query.filter_by(
                repository_id=repo.id, uuid=uuid_, type=tpl_type, parent_case_uuid=None
            ).first()
            if entry is None:
                entry = Template_Repository_Entry(
                    repository_id=repo.id, uuid=uuid_, type=tpl_type, parent_case_uuid=None
                )
                db.session.add(entry)
            entry.title = title_
            entry.version = version_
            entry.description = description_
            entry.download_url = relative_path
            entry.remote_sha = file_sha
            entry.last_synced = now
            upserted.append(entry)

            if tpl_type == "case":
                for task in tpl.get("tasks_template", []):
                    t_uuid = task.get("uuid", "")
                    if not t_uuid:
                        continue
                    t_title = (task.get("title") or task.get("name") or "").strip()
                    t_version = task.get("version")
                    t_description = (task.get("description") or "")[:500]
                    task_entry = Template_Repository_Entry.query.filter_by(
                        repository_id=repo.id, uuid=t_uuid, type="task",
                        parent_case_uuid=uuid_
                    ).first()
                    if task_entry is None:
                        task_entry = Template_Repository_Entry(
                            repository_id=repo.id, uuid=t_uuid, type="task",
                            parent_case_uuid=uuid_
                        )
                        db.session.add(task_entry)
                    task_entry.title = t_title
                    task_entry.version = t_version
                    task_entry.description = t_description
                    task_entry.download_url = None  # embedded tasks have no standalone file
                    task_entry.remote_sha = None
                    task_entry.parent_case_title = title_
                    task_entry.last_synced = now
                    upserted.append(task_entry)

    db.session.commit()
    return [e.to_json() for e in upserted], None




def _norm(v):
    """Normalise a value for diff comparison: strip whitespace, treat empty string as None."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return v


def _display(v):
    """Convert a value to a displayable string for the diff table."""
    if v is None:
        return None
    return str(v)


@templating_blueprint.route("/repositories/<int:rid>/entries/<int:eid>/diff", methods=["GET"])
@login_required
@template_editor_required
def repository_entry_diff(rid, eid):
    """Compare a remote template entry against the local copy field-by-field."""
    entry = Template_Repository_Entry.query.filter_by(id=eid, repository_id=rid).first()
    if not entry:
        return {"message": "Entry not found", "toast_class": "danger-subtle"}, 404

    # ── Fetch remote data ──────────────────────────────────────────────────────
    if entry.parent_case_uuid:
        # Embedded task — use the metadata stored in the DB (no standalone file)
        remote = {
            "title": entry.title,
            "description": entry.description,
            "version": entry.version,
            "time_required": None,
        }
    else:
        repo = Template_Repository.query.get(rid)
        remote, err = _read_entry_file(repo, entry)
        if err:
            return {"message": err, "toast_class": "danger-subtle"}, 200

    # ── Build field list depending on type ────────────────────────────────────
    if entry.type == "case":
        local_obj = Case_Template.query.filter_by(uuid=entry.uuid).first()
        if not local_obj:
            return {"local_exists": False, "has_diff": None, "fields": []}, 200

        local_task_count = Case_Task_Template.query.filter_by(case_id=local_obj.id).count()
        remote_tasks = remote.get("tasks_template", [])
        remote_task_count = len(remote_tasks) if isinstance(remote_tasks, list) else 0

        remote_notes = remote.get("notes")
        if isinstance(remote_notes, list):
            remote_notes = None  # list-form notes can't be meaningfully compared to a string

        raw_fields = [
            ("title",         local_obj.title,           remote.get("title")),
            ("description",   local_obj.description,     remote.get("description")),
            ("version",       local_obj.version,         remote.get("version")),
            ("time_required", local_obj.time_required,   remote.get("time_required")),
            ("notes",         local_obj.notes,           remote_notes),
            ("tasks_count",   local_task_count,          remote_task_count),
        ]

    elif entry.type == "task":
        local_obj = Task_Template.query.filter_by(uuid=entry.uuid).first()
        if not local_obj:
            return {"local_exists": False, "has_diff": None, "fields": []}, 200

        raw_fields = [
            ("title",         local_obj.title,          remote.get("title")),
            ("description",   local_obj.description,    remote.get("description")),
            ("version",       local_obj.version,        remote.get("version")),
            ("time_required", local_obj.time_required,  remote.get("time_required")),
        ]
    else:
        return {"message": f"Unknown entry type: {entry.type}", "toast_class": "warning-subtle"}, 200

    # ── Compare ────────────────────────────────────────────────────────────────
    fields = []
    for field_name, local_val, remote_val in raw_fields:
        match = _norm(local_val) == _norm(remote_val)
        fields.append({
            "field":  field_name,
            "match":  match,
            "local":  _display(local_val),
            "remote": _display(remote_val),
        })

    has_diff = any(not f["match"] for f in fields)
    return {"local_exists": True, "has_diff": has_diff, "fields": fields}, 200


@templating_blueprint.route("/repositories/<int:rid>/entries/<int:eid>/raw", methods=["GET"])
@login_required
@template_editor_required
def repository_entry_raw(rid, eid):
    """Proxy the remote template JSON for viewing in the browser."""
    entry = Template_Repository_Entry.query.filter_by(id=eid, repository_id=rid).first()
    if not entry:
        return {"message": "Entry not found", "toast_class": "danger-subtle"}, 404

    # Embedded tasks don't have their own file — return stored fields as synthetic JSON
    if entry.parent_case_uuid:
        return {
            "uuid": entry.uuid,
            "title": entry.title,
            "version": entry.version,
            "description": entry.description,
            "_note": f"This task is embedded inside case template {entry.parent_case_uuid}. "
                     "Only stored metadata is shown here."
        }, 200

    repo = Template_Repository.query.get(rid)
    data, err = _read_entry_file(repo, entry)
    if err:
        return {"message": err, "toast_class": "danger-subtle"}, 200
    return data, 200


@templating_blueprint.route("/repositories/<int:rid>/entries/<int:eid>/import", methods=["POST"])
@login_required
@template_editor_required
def repository_entry_import(rid, eid):
    """Import a remote template entry into local Case_Template / Task_Template."""
    repo = Template_Repository.query.get(rid)
    if not repo:
        return {"message": "Repository not found", "toast_class": "danger-subtle"}, 404

    entry = Template_Repository_Entry.query.filter_by(id=eid, repository_id=rid).first()
    if not entry:
        return {"message": "Template entry not found", "toast_class": "danger-subtle"}, 404

    now = datetime.datetime.now(tz=datetime.timezone.utc)

    if entry.type == "task":
        if entry.parent_case_uuid:
            # Embedded task: read actual task data from the parent case JSON file
            # so that all fields (including time_required) reflect the remote.
            parent_entry = Template_Repository_Entry.query.filter_by(
                repository_id=rid,
                uuid=entry.parent_case_uuid,
                type="case",
                parent_case_uuid=None,
            ).first()
            task_data_remote = None
            if parent_entry:
                case_tpl, case_err = _read_entry_file(repo, parent_entry)
                if not case_err:
                    for td in case_tpl.get("tasks_template", []):
                        if td.get("uuid") == entry.uuid:
                            task_data_remote = td
                            break
            if task_data_remote:
                tpl_title       = (task_data_remote.get("title") or task_data_remote.get("name") or entry.title or "").strip()
                tpl_description = task_data_remote.get("description") or entry.description or ""
                tpl_version     = task_data_remote.get("version") or entry.version or 1
                tpl_time        = task_data_remote.get("time_required")
            else:
                tpl_title       = entry.title or ""
                tpl_description = entry.description or ""
                tpl_version     = entry.version or 1
                tpl_time        = None
        else:
            tpl, err = _read_entry_file(repo, entry)
            if err:
                return {"message": err, "toast_class": "danger-subtle"}, 200
            tpl_title       = tpl.get("title", "")
            tpl_description = tpl.get("description", "")
            tpl_version     = tpl.get("version", 1)
            tpl_time        = tpl.get("time_required")

        local = Task_Template.query.filter_by(uuid=entry.uuid).first()
        created = local is None
        if local is None:
            local = Task_Template(
                uuid=entry.uuid,
                title=tpl_title,
                description=tpl_description,
                nb_notes=0,
                last_modif=now,
                time_required=tpl_time,
                version=tpl_version,
            )
            db.session.add(local)
        else:
            local.title         = tpl_title
            local.description   = tpl_description
            local.time_required = tpl_time  # always overwrite — remote is authoritative
            local.version       = tpl_version
            local.last_modif    = now
        db.session.commit()
        action = "imported" if created else "updated"
        msg = f"Task template \"{local.title}\" {action} successfully."

    elif entry.type == "case":
        tpl, err = _read_entry_file(repo, entry)
        if err:
            return {"message": err, "toast_class": "danger-subtle"}, 200

        local_case = Case_Template.query.filter_by(uuid=entry.uuid).first()
        created = local_case is None
        if local_case is None:
            local_case = Case_Template(
                uuid=entry.uuid,
                title=tpl.get("title", ""),
                description=tpl.get("description", ""),
                last_modif=now,
                time_required=tpl.get("time_required"),
                notes=tpl.get("notes") if isinstance(tpl.get("notes"), str) else None,
                version=tpl.get("version", 1),
            )
            db.session.add(local_case)
            db.session.flush()  # assign local_case.id without committing
        else:
            local_case.title        = tpl.get("title", local_case.title)
            local_case.description  = tpl.get("description", local_case.description)
            local_case.time_required = tpl.get("time_required")  # always overwrite — remote is authoritative
            local_case.notes        = tpl.get("notes") if isinstance(tpl.get("notes"), str) else local_case.notes
            local_case.version      = tpl.get("version", local_case.version)
            local_case.last_modif   = now

        # Upsert embedded tasks and link to the case
        task_count = 0
        for task_data in tpl.get("tasks_template", []):
            t_uuid = task_data.get("uuid", "")
            if not t_uuid:
                continue
            local_task = Task_Template.query.filter_by(uuid=t_uuid).first()
            if local_task is None:
                local_task = Task_Template(
                    uuid=t_uuid,
                    title=task_data.get("title", ""),
                    description=task_data.get("description", ""),
                    nb_notes=0,
                    last_modif=now,
                    time_required=task_data.get("time_required"),
                    version=task_data.get("version", 1),
                )
                db.session.add(local_task)
                db.session.flush()  # assign local_task.id without committing
            else:
                local_task.title        = task_data.get("title", local_task.title)
                local_task.description  = task_data.get("description", local_task.description)
                local_task.time_required = task_data.get("time_required")  # always overwrite — remote is authoritative
                local_task.version      = task_data.get("version", local_task.version)
                local_task.last_modif   = now

            if not Case_Task_Template.query.filter_by(case_id=local_case.id, task_id=local_task.id).first():
                order = Case_Task_Template.query.filter_by(case_id=local_case.id).count() + 1
                db.session.add(Case_Task_Template(case_id=local_case.id, task_id=local_task.id, case_order_id=order))
            task_count += 1

        db.session.commit()
        action = "imported" if created else "updated"
        msg = f"Case template \"{local_case.title}\" {action} with {task_count} task(s)."
    else:
        return {"message": f"Unknown entry type: {entry.type}", "toast_class": "warning-subtle"}, 200

    flowintel_log("audit", 200, "Template imported from central repository",
                  User=current_user.email, RepositoryId=rid, EntryId=eid, Type=entry.type)

    # Return fresh annotated entries so badges update immediately
    all_entries = Template_Repository_Entry.query.filter_by(repository_id=rid).order_by(
        Template_Repository_Entry.type, Template_Repository_Entry.title
    ).all()
    return {
        "message": msg,
        "toast_class": "success-subtle",
        "entries": _annotate_local_grouped([e.to_json() for e in all_entries]),
    }, 200


@templating_blueprint.route("/repositories/<int:rid>/entries", methods=["GET"])
@login_required
@template_editor_required
def repository_entries(rid):
    repo = Template_Repository.query.get(rid)
    if not repo:
        return {"message": "Repository not found", "toast_class": "danger-subtle"}, 404
    entries = Template_Repository_Entry.query.filter_by(repository_id=rid).order_by(
        Template_Repository_Entry.type, Template_Repository_Entry.title
    ).all()
    return _annotate_local_grouped([e.to_json() for e in entries]), 200


@templating_blueprint.route("/repositories", methods=['GET'])
@login_required
@template_editor_required
def repositories_index():
    """View all central template repositories."""
    manifest_json = json.dumps(current_app.config.get("REPOSITORY_MANIFEST", {}), indent=4)
    return render_template("templating/repositories.html", manifest_json=manifest_json)


@templating_blueprint.route("/repositories/scan", methods=['GET'])
@login_required
@template_editor_required
def repositories_scan():
    """List subdirectories in the configured repository base path.

    Returns each directory with its name, resolved local_path, whether a
    manifest.json is present, and whether it is already registered.
    """
    base_rel = current_app.config.get('REPOSITORY_BASE_PATH', 'modules/repositories')
    base = _repo_base_path(base_rel)

    if not os.path.isdir(base):
        return {"base_path": base_rel, "found": [], "error": f"Directory not found: {base_rel}"}, 200

    existing_paths = {r.local_path for r in Template_Repository.query.with_entities(Template_Repository.local_path).all()}

    found = []
    for entry in sorted(os.listdir(base)):
        full = os.path.join(base, entry)
        if not os.path.isdir(full):
            continue
        rel_path = f"{base_rel}/{entry}"
        has_manifest = os.path.isfile(os.path.join(full, 'manifest.json'))
        name = entry
        if has_manifest:
            try:
                import json as _json
                with open(os.path.join(full, 'manifest.json'), 'r', encoding='utf-8') as f:
                    mf = _json.load(f)
                name = mf.get('name') or entry
            except Exception:
                pass
        found.append({
            "name": name,
            "dir": entry,
            "local_path": rel_path,
            "has_manifest": has_manifest,
            "already_added": rel_path in existing_paths,
        })

    return {"base_path": base_rel, "found": found}, 200


@templating_blueprint.route("/repositories/list", methods=['GET'])
@login_required
@template_editor_required
def repositories_list():
    """Return all repositories as JSON."""
    repos = Template_Repository.query.order_by(Template_Repository.name).all()
    return {"repositories": [r.to_json() for r in repos]}, 200


@templating_blueprint.route("/repositories/add", methods=['POST'])
@login_required
@template_editor_required
def repository_add():
    """Create a new template repository."""
    data = request.json or {}
    name = (data.get("name") or "").strip()
    local_path = (data.get("local_path") or "").strip()
    if not name or not local_path:
        return {"message": "Name and local path are required", "toast_class": "warning-subtle"}, 400

    repo = Template_Repository(
        name=name,
        description=(data.get("description") or "").strip() or None,
        url=(data.get("url") or "").strip() or None,
        local_path=local_path,
    )
    db.session.add(repo)
    db.session.commit()
    flowintel_log("audit", 201, "Template repository added",
                  User=current_user.email, RepositoryId=repo.id, Name=name)
    return {"message": f"Repository '{name}' added", "toast_class": "success-subtle",
            "repository": repo.to_json()}, 201


@templating_blueprint.route("/repositories/<int:rid>/edit", methods=['POST'])
@login_required
@template_editor_required
def repository_edit(rid):
    """Edit an existing template repository."""
    repo = Template_Repository.query.get(rid)
    if not repo:
        return {"message": "Repository not found", "toast_class": "danger-subtle"}, 404

    data = request.json or {}
    name = (data.get("name") or "").strip()
    local_path = (data.get("local_path") or "").strip()
    if not name or not local_path:
        return {"message": "Name and local path are required", "toast_class": "warning-subtle"}, 400

    repo.name = name
    repo.description = (data.get("description") or "").strip() or None
    repo.url = (data.get("url") or "").strip() or None
    repo.local_path = local_path
    db.session.commit()
    flowintel_log("audit", 200, "Template repository edited",
                  User=current_user.email, RepositoryId=repo.id, Name=name)
    return {"message": f"Repository '{name}' edited", "toast_class": "success-subtle",
            "repository": repo.to_json()}, 200


@templating_blueprint.route("/repositories/<int:rid>/delete", methods=['POST'])
@login_required
@template_editor_required
def repository_delete(rid):
    """Delete a template repository."""
    repo = Template_Repository.query.get(rid)
    if not repo:
        return {"message": "Repository not found", "toast_class": "danger-subtle"}, 404

    name = repo.name
    db.session.delete(repo)
    db.session.commit()
    flowintel_log("audit", 200, "Template repository deleted",
                  User=current_user.email, RepositoryId=rid, Name=name)
    return {"message": f"Repository '{name}' deleted", "toast_class": "success-subtle"}, 200
