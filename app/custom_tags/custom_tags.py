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
    """List all cases"""
    return render_template("custom_tags/custom_tags_index.html")

@custom_tags_blueprint.route("/add", methods=['GET', 'POST'])
@login_required
@editor_required
def add_custom_tag():
    """List all cases"""
    form = AddCustomTagForm()
    if form.validate_on_submit() and CustomCore.add_custom_tag_core(form_to_dict(form)):
        return redirect("/custom_tags/")
    return render_template("custom_tags/add_custom_tag.html", form=form)


@custom_tags_blueprint.route("/list", methods=['GET', 'POST'])
@login_required
def list():
    """List all custom tags"""
    return [c_t.to_json() for c_t in CustomCore.get_custom_tags()]

@custom_tags_blueprint.route("/<ctid>/delete_custom_tag", methods=['GET', 'POST'])
@login_required
@editor_required
def delete_custom_tag(ctid):
    """Delete a custom tag"""
    if CustomCore.get_custom_tag(ctid):
        if CustomCore.delete_custom_tag(ctid):
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
    print(request.json)
    if "custom_tag_id" in request.json["result_dict"] and request.json["result_dict"]["custom_tag_id"]:
        if "custom_tag_name" in request.json["result_dict"] and request.json["result_dict"]["custom_tag_name"]:
            if "custom_tag_color" in request.json["result_dict"] and request.json["result_dict"]["custom_tag_color"]:
                if "custom_tag_icon" not in request.json["result_dict"] or not request.json["result_dict"]["custom_tag_icon"]:
                    request.json["result_dict"]["custom_tag_icon"] = ""
                    
                res = CustomCore.change_config_core(request.json["result_dict"])
                if res:
                    return {'message': 'Config changed', 'toast_class': "success-subtle"}, 200
                return {'message': 'Something went wrong', 'toast_class': "danger-subtle"}, 400                    
            return {'message': 'Need to pass "custom_tag_color"', 'toast_class': "warning-subtle"}, 400
        return {'message': 'Need to pass "custom_tag_name"', 'toast_class': "warning-subtle"}, 400
    return {'message': 'Need to pass "custom_tag_id"', 'toast_class': "warning-subtle"}, 400

