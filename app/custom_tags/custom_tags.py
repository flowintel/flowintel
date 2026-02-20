from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user
from .form import AddCustomTagForm
from ..db_class.db import Task_Template, Case_Template
from ..decorators import editor_required
from ..utils.utils import form_to_dict
from . import custom_tags_core as CustomCore

custom_tags_blueprint = Blueprint(
    'custom tags',
    __name__,
    template_folder='templates',
    static_folder='static'
)

##########
# Render #
##########


@custom_tags_blueprint.route("/", methods=['GET', 'POST'])
@login_required
def index():
    """Custom tags index page"""
    return render_template("custom_tags/custom_tags_index.html")

@custom_tags_blueprint.route("/add", methods=['GET', 'POST'])
@login_required
@editor_required
def add_custom_tag():
    """Add a new custom tag"""
    from ..utils.logger import flowintel_log
    form = AddCustomTagForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        custom_tag = CustomCore.add_custom_tag_core(form_dict)
        if custom_tag:
            flowintel_log("audit", 201, "Custom tag created", User=current_user.email, CustomTagId=custom_tag.id, CustomTagName=custom_tag.name)
            return redirect("/custom_tags/")
    return render_template("custom_tags/add_custom_tag.html", form=form)


@custom_tags_blueprint.route("/list", methods=['GET', 'POST'])
@login_required
def list():
    """List all custom tags"""
    q = request.args.get('q', None, type=str)
    tags = []
    for c_t in CustomCore.get_custom_tags():
        tag_json = c_t.to_json()
        tag_json['in_use'] = CustomCore.is_custom_tag_in_use(c_t.id)
        tags.append(tag_json)
    if q:
        ql = q.lower()
        tags = [t for t in tags if ql in t.get('name','').lower()]
    return tags

@custom_tags_blueprint.route("/<ctid>/usage", methods=['GET'])
@login_required
def get_custom_tag_usage(ctid):
    """Get cases and tasks using a specific custom tag"""
    if CustomCore.get_custom_tag(ctid):
        cases = CustomCore.get_cases_using_custom_tag(ctid)
        tasks = CustomCore.get_tasks_using_custom_tag(ctid)
        return {"cases": cases, "tasks": tasks}, 200
    return {"message": "Custom tag not found", 'toast_class': "danger-subtle"}, 404

@custom_tags_blueprint.route("/<ctid>/delete_custom_tag", methods=['GET', 'POST'])
@login_required
@editor_required
def delete_custom_tag(ctid):
    """Delete a custom tag"""
    from ..utils.logger import flowintel_log
    custom_tag = CustomCore.get_custom_tag(ctid)
    if custom_tag:
        tag_name = custom_tag.name
        if CustomCore.delete_custom_tag(ctid):
            flowintel_log("audit", 200, "Custom tag deleted", User=current_user.email, CustomTagId=ctid, CustomTagName=tag_name)
            return {"message": "Custom tag deleted", "toast_class": "success-subtle"}, 200
        return {"message": "Error custom tag deleted", 'toast_class': "danger-subtle"}, 400
    return {"message": "Custom tag not found", 'toast_class': "danger-subtle"}, 404

@custom_tags_blueprint.route("/change_status", methods=['GET', 'POST'])
@login_required
@editor_required
def change_status():
    """Active or disabled a Custom tag"""
    if "custom_tag_id" in request.args:
        res = CustomCore.change_status_core(request.args.get("custom_tag_id"))
        if res:
            return {'message': 'Custom tag status changed', 'toast_class': "success-subtle"}, 200
        return {'message': 'Something went wrong', 'toast_class': "danger-subtle"}, 400
    return {'message': 'Need to pass "custom_tag_id"', 'toast_class': "warning-subtle"}, 400


@custom_tags_blueprint.route("/change_config", methods=['GET', 'POST'])
@login_required
@editor_required
def change_config():
    """Change configuration for a custom tag"""
    from ..utils.logger import flowintel_log
    if "custom_tag_id" in request.json["result_dict"] and request.json["result_dict"]["custom_tag_id"]:
        if "custom_tag_name" in request.json["result_dict"] and request.json["result_dict"]["custom_tag_name"]:
            if "custom_tag_color" in request.json["result_dict"] and request.json["result_dict"]["custom_tag_color"]:
                if "custom_tag_icon" not in request.json["result_dict"] or not request.json["result_dict"]["custom_tag_icon"]:
                    request.json["result_dict"]["custom_tag_icon"] = ""
                    
                res = CustomCore.change_config_core(request.json["result_dict"])
                if res:
                    flowintel_log("audit", 200, "Custom tag edited", User=current_user.email, CustomTagId=request.json["result_dict"]["custom_tag_id"], CustomTagName=request.json["result_dict"]["custom_tag_name"])
                    return {'message': 'Config changed', 'toast_class': "success-subtle"}, 200
                return {'message': 'Something went wrong', 'toast_class': "danger-subtle"}, 400                    
            return {'message': 'Need to pass "custom_tag_color"', 'toast_class': "warning-subtle"}, 400
        return {'message': 'Need to pass "custom_tag_name"', 'toast_class': "warning-subtle"}, 400
    return {'message': 'Need to pass "custom_tag_id"', 'toast_class': "warning-subtle"}, 400

