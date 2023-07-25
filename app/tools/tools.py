from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user
from . import tools_core as ToolsModel
from ..decorators import editor_required
from .form import TaskTemplateForm, CaseTemplateForm, TaskTemplateEditForm
from ..utils.utils import form_to_dict

tools_blueprint = Blueprint(
    'tools',
    __name__,
    template_folder='templates',
    static_folder='static'
)


##########
# Render #
##########


@tools_blueprint.route("/templates/case", methods=['GET'])
@login_required
def case_templates_index():
    return render_template("tools/case_templates_index.html")

@tools_blueprint.route("/templates/task", methods=['GET', "POST"])
@login_required
def task_template_view():
    form = TaskTemplateForm()
    task_template_query_list = ToolsModel.get_all_task_templates()
    form.tasks.choices = [(template.id, template.title) for template in task_template_query_list]
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        template = ToolsModel.add_task_template_core(form_dict)
        return redirect(f"/tools/templates/task")
    return render_template("tools/task_template.html", form=form)


@tools_blueprint.route("/add_template", methods=['GET','POST'])
@login_required
@editor_required
def add_template():
    """Add a new Template"""

    form = CaseTemplateForm()

    task_template_query_list = ToolsModel.get_all_task_templates()
    form.tasks.choices = [(template.id, template.title) for template in task_template_query_list]
    
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        template = ToolsModel.add_case_template_core(form_dict)
        flash("Template created", "success")
        return redirect(f"/tools/template/case/view/{template.id}")

    return render_template("tools/add_templates.html", form=form)


@tools_blueprint.route("/template/case/view/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def case_template_view(cid):
    """View a Template"""
    template = ToolsModel.get_case_template(cid)
    if template:
        case = template.to_json()

        form_task = TaskTemplateForm()
        task_template_query_list = ToolsModel.get_all_task_templates()
        task_by_case = ToolsModel.get_task_by_case(cid)
        task_id_list = [tid.id for tid in task_by_case]
        form_task.tasks.choices = [(template.id, template.title) for template in task_template_query_list if template.id not in task_id_list]
        if form_task.validate_on_submit():
            form_dict = form_to_dict(form_task)
            ToolsModel.add_task_case_template(form_dict, cid)
            return redirect(f"/tools/template/case/view/{cid}")

        return render_template("tools/case_template_view.html", case=case, form_task=form_task)
    return render_template("404.html")


@tools_blueprint.route("/template/edit_task/<tid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_task(tid):
    """edit a task Template"""
    template = ToolsModel.get_task_template(tid)
    if template:
        form = TaskTemplateEditForm()
        
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            template = ToolsModel.edit_task_template(form_dict, tid)
            flash("Template edited", "success")
            return redirect(f"/tools/templates/task")
        else:
            form.title.data = template.title
            form.body.data = template.description
            form.url.data = template.url

        return render_template("tools/edit_task.html", form=form)
    return render_template("404.html")


@tools_blueprint.route("/get_all_case_templates", methods=['GET'])
@login_required
@editor_required
def get_all_case_templates():
    page = request.args.get('page', 1, type=int)
    templates = ToolsModel.get_page_case_templates(page)
    for template in templates:
        templates_list = list()
        loc_template = template.to_json()
        loc_template["current_user_permission"] = ToolsModel.get_role(current_user).to_json()
        templates_list.append(loc_template)
    return {"templates": templates_list, "nb_pages": templates.pages}


@tools_blueprint.route("/get_case_template/<cid>", methods=['GET'])
@login_required
@editor_required
def get_template(cid):
    """View a Template"""
    template = ToolsModel.get_case_template(cid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@tools_blueprint.route("/get_task_template/<tid>", methods=['GET'])
@login_required
@editor_required
def get_task_template(tid):
    """View a Template"""
    template = ToolsModel.get_task_template(tid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@tools_blueprint.route("/get_all_task_templates", methods=['GET'])
@login_required
@editor_required
def get_all_task_templates():
    """View a Template"""
    page = request.args.get('page', 1, type=int)
    templates = ToolsModel.get_page_task_templates(page)
    if templates:
        templates_list = list()
        for template in templates:
            loc_template = template.to_json()
            loc_template["current_user_permission"] = ToolsModel.get_role(current_user).to_json()
            templates_list.append(loc_template)
        return {"templates": templates_list, "nb_pages": templates.pages}
    return {"message": "Template not found"}


@tools_blueprint.route("/get_task_by_case/<cid>", methods=['GET'])
@login_required
@editor_required
def get_task_by_case(cid):
    """View a Template"""
    templates = ToolsModel.get_task_by_case(cid)
    if templates:
        templates_list = list()
        for template in templates:
            loc_template = template.to_json()
            loc_template["current_user_permission"] = ToolsModel.get_role(current_user).to_json()
            templates_list.append(loc_template)
        return {"tasks": templates_list}
    return {"message": "Template not found"}


@tools_blueprint.route("/template/<cid>/remove_task/<tid>", methods=['GET'])
@login_required
@editor_required
def remove_task(cid, tid):
    """remove task form case"""
    if ToolsModel.get_task_template(tid):
        if ToolsModel.remove_task_case(cid, tid):
            return {"message":"Task Template removed", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template removed", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@tools_blueprint.route("/template/delete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def delete_task(tid):
    """delete a task template"""
    if ToolsModel.get_task_template(tid):
        if ToolsModel.delete_task_template(tid):
            return {"message":"Task Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@tools_blueprint.route("/template/delete_case/<cid>", methods=['GET'])
@login_required
@editor_required
def delete_case(cid):
    """delete a case template"""
    if ToolsModel.get_case_template(cid):
        if ToolsModel.delete_case_template(cid):
            return {"message":"Case Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Case Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@tools_blueprint.route("/template/create_case_from_template/<cid>", methods=['POST'])
@login_required
@editor_required
def create_case_from_template(cid):
    """Create a case from a template"""
    template = ToolsModel.get_case_template(cid)
    if template:
        case_title_fork = request.json["case_title_fork"]
        new_case = ToolsModel.create_case_from_template(cid, case_title_fork, current_user)
        if type(new_case) == dict:
            return new_case
        return {"new_case_id": new_case.id}, 201
    return {"message": "Template not found"}