import ast
from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user
from .TemplateCase import TemplateModel
from . import common_template_core as CommonModel
from .TaskTemplateCore import TaskModel
from ..decorators import editor_required
from .form import TaskTemplateForm, CaseTemplateForm, TaskTemplateEditForm, CaseTemplateEditForm
from ..utils.utils import form_to_dict
from ..utils.formHelper import prepare_tags
from ..case import common_core as CommonCaseModel

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
@editor_required
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
            template = TemplateModel.create_case(form_dict)
            flash("Template created", "success")
            return redirect(f"/templating/case/{template.id}")
        return render_template("templating/create_case_template.html", form=form)
    return render_template("templating/create_case_template.html", form=form)


@templating_blueprint.route("/create_task", methods=['GET','POST'])
@login_required
@editor_required
def create_task_template():
    """Create a task Template"""
    form = TaskTemplateForm()
    form.tasks.choices = [(template.id, template.title) for template in  CommonModel.get_all_task_templates()]
    if form.validate_on_submit():
        res = prepare_tags(request)
        if isinstance(res, dict):
            form_dict = form_to_dict(form)
            form_dict.update(res)
            template = TaskModel.add_task_template_core(form_dict)
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
        case = template.to_json()
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
@editor_required
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
            TemplateModel.add_task_case_template(form_dict, cid)
            flash("Template added", "success")
            return redirect(f"/templating/case/{cid}")
        return render_template("templating/add_task_case.html", form=form)
    return render_template("templating/add_task_case.html", form=form)


@templating_blueprint.route("/edit_case/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_case(cid):
    """Edit a case Template"""
    template = CommonModel.get_case_template(cid)
    if template:
        form = CaseTemplateEditForm()
        form.template_id.data = cid
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            template = TemplateModel.edit(form_dict, cid)
            flash("Template edited", "success")
            return redirect(f"/templating/case/{cid}")
        else:
            form.title.data = template.title
            form.description.data = template.description
            form.time_required.data = template.time_required

        return render_template("templating/edit_case_template.html", form=form)
    return render_template("404.html")

@templating_blueprint.route("/case/edit_tags/<cid>", methods=['GET','POST'])
@login_required
@editor_required
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
                return {"message": "Tags edited", "toast_class": "success-subtle"}, 200
            return {"message": "Error with Clusters", "toast_class": "warning-subtle"}, 400
        return {"message": "Error with Tags", "toast_class": "warning-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/edit_task/<tid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_task(tid):
    """Edit a task Template"""
    template = CommonModel.get_task_template(tid)
    if template:
        form = TaskTemplateEditForm()
        form.template_id.data = tid
        if form.validate_on_submit():
            res = prepare_tags(request)
            if isinstance(res, dict):
                form_dict = form_to_dict(form)
                form_dict.update(res)
                template = TaskModel.edit_task_template(form_dict, tid)
                flash("Template edited", "success")
                return redirect(f"/templating/tasks")
            return render_template("templating/edit_task_template.html", form=form)
        else:
            form.title.data = template.title
            form.description.data = template.description
            form.time_required.data = template.time_required

        return render_template("templating/edit_task_template.html", form=form)
    return render_template("404.html")


@templating_blueprint.route("/get_all_case_templates", methods=['GET'])
@login_required
@editor_required
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
@editor_required
def get_page_case_templates():
    """Get a page of case templates"""
    page = request.args.get('page', 1, type=int)
    title_filter = request.args.get('title')
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
                                        or_and_galaxies)

    templates_list = list()
    for template in templates:
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        templates_list.append(loc_template)
    return {"templates": templates_list, "nb_pages": nb_pages}


@templating_blueprint.route("/get_case_template/<cid>", methods=['GET'])
@login_required
@editor_required
def get_template(cid):
    """Get a case template"""
    template = CommonModel.get_case_template(cid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@templating_blueprint.route("/get_task_template/<tid>", methods=['GET'])
@login_required
@editor_required
def get_task_template(tid):
    """Get a task template"""
    template = CommonModel.get_task_template(tid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@templating_blueprint.route("/get_all_task_templates", methods=['GET'])
@login_required
@editor_required
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
@editor_required
def get_page_task_templates():
    """Get a page of task template"""
    page = request.args.get('page', 1, type=int)
    title_filter = request.args.get('title')
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

    templates, nb_pages = TaskModel.sort_tasks(page, 
                                                title_filter, 
                                                taxonomies, 
                                                galaxies, 
                                                tags, 
                                                clusters,
                                                custom_tags,
                                                or_and_taxo, 
                                                or_and_galaxies)

    if templates:
        templates_list = list()
        for template in templates:
            templates_list.append(TemplateModel.regroup_task_info(template, current_user))
        return {"templates": templates_list, "nb_pages": nb_pages}
    return {"message": "Template not found"}


@templating_blueprint.route("/get_task_by_case/<cid>", methods=['GET'])
@login_required
@editor_required
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
@editor_required
def remove_task(cid, tid):
    """Remove a task template form a case template"""
    if CommonModel.get_task_template(tid):
        if TemplateModel.remove_task_case(cid, tid):
            return {"message":"Task Template removed", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template removed", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/delete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def delete_task(tid):
    """Delete a task template"""
    if CommonModel.get_task_template(tid):
        if TaskModel.delete_task_template(tid):
            return {"message":"Task Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/delete_case/<cid>", methods=['GET'])
@login_required
@editor_required
def delete_case(cid):
    """Delete a case template"""
    if CommonModel.get_case_template(cid):
        if TemplateModel.delete_case(cid):
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
@editor_required
def modif_note_case(cid):
    """Modify note of the task"""
    if CommonModel.get_case_template(cid):
        notes = request.json["notes"]
        if TemplateModel.modif_note_core(cid, notes):
            return {"message": "Notes modified", "toast_class": "success-subtle"}, 200
        return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@templating_blueprint.route("/task/<tid>/create_note", methods=['GET'])
@login_required
@editor_required
def task_create_note(tid):
    """Create a new note for the template"""
    res_note = TaskModel.create_note(tid)
    if res_note:
        return {"note": res_note.to_json(), "message": "Note created", "toast_class": "success-subtle"}, 200
    return {"message": "Error create note", "toast_class": "danger-subtle"}, 400

@templating_blueprint.route("/task/<tid>/delete_note", methods=['GET'])
@login_required
@editor_required
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
@editor_required
def task_modif_note(tid):
    """Modify note of the task"""
    if CommonModel.get_task_template(tid):
        notes = request.json["notes"]
        if "note_id" in request.args:
            res_note = TaskModel.modif_note_core(tid, notes, request.args.get("note_id"))
            if res_note:
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
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


@templating_blueprint.route("/case/<cid>/change_order/<tid>", methods=['GET'])
@login_required
@editor_required
def change_order(cid, tid):
    """Change the order of tasks"""
    case = CommonModel.get_case_template(cid)
    if case:
        task = CommonModel.get_task_template(tid)
        if task:
            up_down = None
            if "up_down" in request.args:
                up_down = request.args.get("up_down")
                TaskModel.change_order(case, task, up_down)
                return {"message": "Order changed", 'toast_class': "success-subtle"}, 200
            return {"message": "Need to pass up_down", 'toast_class': "danger-subtle"}, 400
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
@editor_required
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
@editor_required
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
@editor_required
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
@editor_required
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
@editor_required
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
@editor_required
def delete_url_tool(tid, utid):
    """Delete a Url/Tool"""
    task = CommonModel.get_task_template(tid)
    if task:
        if TaskModel.delete_url_tool(tid, utid):
            return {"message": "Url/Tool deleted", 'toast_class': "success-subtle", "icon": "fas fa-trash"}, 200 
        return {"message": "Url/Tool not found", 'toast_class': "danger-subtle"}, 404
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404
