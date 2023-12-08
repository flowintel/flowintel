from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user
from . import tools_core as ToolsModel
from . import common_template_core as CommonModel
from . import task_template_core as TaskModel
from ..decorators import editor_required
from .form import TaskTemplateForm, CaseTemplateForm, TaskTemplateEditForm, CaseTemplateEditForm
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

@tools_blueprint.route("/template/cases", methods=['GET'])
@login_required
def case_templates_index():
    """View all case templates"""
    return render_template("tools/case_templates_index.html")

@tools_blueprint.route("/template/tasks", methods=['GET', "POST"])
@login_required
def task_template_view():
    """View all task templates"""
    return render_template("tools/task_template.html")


@tools_blueprint.route("/template/create_case", methods=['GET','POST'])
@login_required
@editor_required
def create_case_template():
    """Create a case Template"""
    form = CaseTemplateForm()

    task_template_query_list = CommonModel.get_all_task_templates()
    form.tasks.choices = [(template.id, template.title) for template in task_template_query_list]
    
    if form.validate_on_submit():
        tag_list = request.form.getlist("tags_select")
        cluster_list = request.form.getlist("clusters_select")
        if CommonModel.check_tag(tag_list):
            if CommonModel.check_cluster(cluster_list):
                form_dict = form_to_dict(form)
                form_dict["tags"] = tag_list
                form_dict["clusters"] = cluster_list
                template = ToolsModel.create_case_template(form_dict)
                flash("Template created", "success")
                return redirect(f"/tools/template/case/{template.id}")
            return render_template("case/create_case_template.html", form=form)
        return render_template("case/create_case_template.html", form=form)
    return render_template("tools/create_case_template.html", form=form)


@tools_blueprint.route("/template/create_task", methods=['GET','POST'])
@login_required
@editor_required
def create_task_template():
    """Create a task Template"""
    form = TaskTemplateForm()
    form.tasks.choices = [(template.id, template.title) for template in  CommonModel.get_all_task_templates()]
    if form.validate_on_submit():
        tag_list = request.form.getlist("tags_select")
        cluster_list = request.form.getlist("clusters_select")
        connector_list = request.form.getlist("connectors_select")
        if CommonModel.check_tag(tag_list):
            if CommonModel.check_cluster(cluster_list):
                form_dict = form_to_dict(form)
                form_dict["tags"] = tag_list
                form_dict["clusters"] = cluster_list
                form_dict["connectors"] = connector_list
                template = TaskModel.add_task_template_core(form_dict)
                flash("Template created", "success")
                return redirect(f"/tools/template/tasks")
            return render_template("case/create_task_template.html", form=form)
        return render_template("case/create_task_template.html", form=form)
    return render_template("tools/create_task_template.html", form=form)


@tools_blueprint.route("/template/case/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def case_template_view(cid):
    """View a case Template"""
    template = CommonModel.get_case_template(cid)
    if template:
        case = template.to_json()
        return render_template("tools/case_template_view.html", case=case)
    return render_template("404.html")

@tools_blueprint.route("/template/case/<cid>/add_task", methods=['GET','POST'])
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
        tag_list = request.form.getlist("tags_select")
        cluster_list = request.form.getlist("clusters_select")
        if CommonModel.check_tag(tag_list):
            if CommonModel.check_cluster(cluster_list):
                form_dict = form_to_dict(form)
                form_dict["tags"] = tag_list
                form_dict["clusters"] = cluster_list
                ToolsModel.add_task_case_template(form_dict, cid)
                flash("Template added", "success")
                return redirect(f"/tools/template/case/{cid}")
            return render_template("tools/add_task_case.html", form=form)
        return render_template("tools/add_task_case.html", form=form)
    return render_template("tools/add_task_case.html", form=form)


@tools_blueprint.route("/template/edit_case/<cid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_case(cid):
    """Edit a case Template"""
    template = CommonModel.get_case_template(cid)
    if template:
        form = CaseTemplateEditForm()
        form.template_id.data = cid
        if form.validate_on_submit():
            tag_list = request.form.getlist("tags_select")
            cluster_list = request.form.getlist("clusters_select")
            if CommonModel.check_tag(tag_list):
                if CommonModel.check_cluster(cluster_list):
                    form_dict = form_to_dict(form)
                    form_dict["tags"] = tag_list
                    form_dict["clusters"] = cluster_list
                    template = ToolsModel.edit_case_template(form_dict, cid)
                    flash("Template edited", "success")
                    return redirect(f"/tools/template/case/{cid}")
                return render_template("tools/edit_case_template.html", form=form)
            return render_template("tools/edit_case_template.html", form=form)
        else:
            form.title.data = template.title
            form.description.data = template.description

        return render_template("tools/edit_case_template.html", form=form)
    return render_template("404.html")


@tools_blueprint.route("/template/edit_task/<tid>", methods=['GET','POST'])
@login_required
@editor_required
def edit_task(tid):
    """Edit a task Template"""
    template = CommonModel.get_task_template(tid)
    if template:
        form = TaskTemplateEditForm()
        form.template_id.data = tid
        if form.validate_on_submit():
            tag_list = request.form.getlist("tags_select")
            cluster_list = request.form.getlist("clusters_select")
            connector_list = request.form.getlist("connectors_select")
            if CommonModel.check_tag(tag_list):
                if CommonModel.check_cluster(cluster_list):
                    form_dict = form_to_dict(form)
                    form_dict["tags"] = tag_list
                    form_dict["clusters"] = cluster_list
                    form_dict["connectors"] = connector_list
                    template = TaskModel.edit_task_template(form_dict, tid)
                    flash("Template edited", "success")
                    return redirect(f"/tools/template/tasks")
                return render_template("tools/edit_task_template.html", form=form)
            return render_template("tools/edit_task_template.html", form=form)
        else:
            form.title.data = template.title
            form.body.data = template.description
            form.url.data = template.url

        return render_template("tools/edit_task_template.html", form=form)
    return render_template("404.html")


@tools_blueprint.route("/get_all_case_templates", methods=['GET'])
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


@tools_blueprint.route("/get_page_case_templates", methods=['GET'])
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

    templates, nb_pages = ToolsModel.get_page_case_templates(page, title_filter, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies)
    templates_list = list()
    for template in templates:
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        templates_list.append(loc_template)
    return {"templates": templates_list, "nb_pages": nb_pages}


@tools_blueprint.route("/get_case_template/<cid>", methods=['GET'])
@login_required
@editor_required
def get_template(cid):
    """Get a case template"""
    template = CommonModel.get_case_template(cid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@tools_blueprint.route("/get_task_template/<tid>", methods=['GET'])
@login_required
@editor_required
def get_task_template(tid):
    """Get a task template"""
    template = CommonModel.get_task_template(tid)
    if template:
        return {"template": template.to_json()}
    return {"message": "Template not found"}


@tools_blueprint.route("/get_all_task_templates", methods=['GET'])
@login_required
@editor_required
def get_all_task_templates():
    """Get all task templates"""
    templates = CommonModel.get_all_task_templates()
    templates_list = list()
    for template in templates:
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        loc_template["instances"] = TaskModel.get_task_info(template)
        templates_list.append(loc_template)
    return {"templates": templates_list}


@tools_blueprint.route("/get_page_task_templates", methods=['GET'])
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

    templates, nb_pages = TaskModel.get_page_task_templates(page, title_filter, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies)
    if templates:
        templates_list = list()
        for template in templates:
            loc_template = template.to_json()
            loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
            loc_template["instances"] = TaskModel.get_task_info(template)
            templates_list.append(loc_template)
        return {"templates": templates_list, "nb_pages": nb_pages}
    return {"message": "Template not found"}


@tools_blueprint.route("/get_task_by_case/<cid>", methods=['GET'])
@login_required
@editor_required
def get_task_by_case(cid):
    """Get a task template by a case template"""
    templates = CommonModel.get_task_by_case(cid)
    if templates:
        templates_list = list()
        for template in templates:
            loc_template = template.to_json()
            loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
            loc_template["instances"] = TaskModel.get_task_info(template)
            templates_list.append(loc_template)
        return {"tasks": templates_list}
    return {"tasks": []}


@tools_blueprint.route("/template/<cid>/remove_task/<tid>", methods=['GET'])
@login_required
@editor_required
def remove_task(cid, tid):
    """Remove a task template form a case template"""
    if CommonModel.get_task_template(tid):
        if ToolsModel.remove_task_case(cid, tid):
            return {"message":"Task Template removed", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template removed", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@tools_blueprint.route("/template/delete_task/<tid>", methods=['GET'])
@login_required
@editor_required
def delete_task(tid):
    """Delete a task template"""
    if CommonModel.get_task_template(tid):
        if TaskModel.delete_task_template(tid):
            return {"message":"Task Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Task Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@tools_blueprint.route("/template/delete_case/<cid>", methods=['GET'])
@login_required
@editor_required
def delete_case(cid):
    """Delete a case template"""
    if CommonModel.get_case_template(cid):
        if ToolsModel.delete_case_template(cid):
            return {"message":"Case Template deleted", "toast_class": "success-subtle"}, 200
        return {"message":"Error Case Template deleted", "toast_class": "danger-subtle"}, 400
    return {"message":"Template not found", "toast_class": "danger-subtle"}, 404


@tools_blueprint.route("/template/create_case_from_template/<cid>", methods=['POST'])
@login_required
@editor_required
def create_case_from_template(cid):
    """Create a case from a template"""
    template = CommonModel.get_case_template(cid)
    if template:
        case_title_fork = request.json["case_title_fork"]
        new_case = ToolsModel.create_case_from_template(cid, case_title_fork, current_user)
        if type(new_case) == dict:
            return new_case
        return {"new_case_id": new_case.id}, 201
    return {"message": "Template not found"}


@tools_blueprint.route("/template/case/<cid>/download", methods=['GET'])
@login_required
@editor_required
def download_case(cid):
    """Download a case template"""
    case = CommonModel.get_case_template(cid)
    task_list = [task.download() for task in CommonModel.get_task_by_case(cid)]
    return_dict = case.download()
    return_dict["tasks_template"] = task_list
    return jsonify(return_dict), 200, {'Content-Disposition': f'attachment; filename=template_case_{case.title}.json'}





@tools_blueprint.route("/importer_view", methods=['GET'])
@login_required
@editor_required
def importer_view():
    """Importer view"""
    return render_template("tools/importer.html")


@tools_blueprint.route("/importer", methods=['POST'])
@login_required
@editor_required
def importer():
    """Import case and task"""
    if len(request.files) > 0:
        message = ToolsModel.read_json_file(request.files, current_user)
        if message:
            message["toast_class"] = "danger-subtle"
            return message, 400
        return {"message": "All created", "toast_class": "success-subtle"}, 200
    

@tools_blueprint.route("/template/get_taxonomies_case/<cid>", methods=['GET'])
@login_required
def get_taxonomies_case(cid):
    case = CommonModel.get_case_template(cid)
    if case:
        tags = CommonModel.get_case_template_tags(case.id)
        taxonomies = []
        if tags:
            taxonomies = [tag.split(":")[0] for tag in tags]
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@tools_blueprint.route("/template/get_taxonomies_task/<tid>", methods=['GET'])
@login_required
def get_taxonomies_task(tid):
    task = CommonModel.get_task_template(tid)
    if task:
        tags = CommonModel.get_task_template_tags(task.id)
        taxonomies = []
        if tags:
            taxonomies = [tag.split(":")[0] for tag in tags]
        return {"tags": tags, "taxonomies": taxonomies}
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


@tools_blueprint.route("/template/get_galaxies_case/<cid>", methods=['GET'])
@login_required
def get_galaxies_case(cid):
    case = CommonModel.get_case_template(cid)
    if case:
        clusters = CommonModel.get_case_clusters(case.id)
        galaxies = []
        if clusters:
            for cluster in clusters:
                loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                if not loc_g.name in galaxies:
                    galaxies.append(loc_g.name)
                index = clusters.index(cluster)
                clusters[index] = cluster.tag
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404

@tools_blueprint.route("/template/get_galaxies_task/<tid>", methods=['GET'])
@login_required
def get_galaxies_task(tid):
    task = CommonModel.get_task_template(tid)
    if task:
        clusters = CommonModel.get_task_clusters(task.id)
        galaxies = []
        if clusters:
            for cluster in clusters:
                loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                if not loc_g.name in galaxies:
                    galaxies.append(loc_g.name)
                index = clusters.index(cluster)
                clusters[index] = cluster.tag
        return {"clusters": clusters, "galaxies": galaxies}
    return {"message": "Task Not found", 'toast_class': "danger-subtle"}, 404


@tools_blueprint.route("/template/get_connectors_task/<tid>", methods=['GET'])
@login_required
def get_connectors_task(tid):
    task = CommonModel.get_task_template(tid)
    if task:
        return {"connectors": [CommonModel.get_instance(task_instance.instance_id).name for task_instance in CommonModel.get_task_connectors(task.id) ]}
    return {"message": "task Not found", 'toast_class': "danger-subtle"}, 404