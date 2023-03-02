from .. import db
from ..db_class.db import Case, Task
from flask import Blueprint, render_template, redirect, jsonify
import re
from .form import CaseForm, TaskForm
from flask_login import login_required
from . import case_core as CaseModel
import json

case_blueprint = Blueprint(
    'case',
    __name__,
    template_folder='templates',
    static_folder='static'
)



@case_blueprint.route("/", methods=['GET'])
@login_required
def index():
    return render_template("case/case_index.html")


@case_blueprint.route("case/get_cases", methods=['GET'])
@login_required
def get_cases():
    cases = CaseModel.getAll()
    return jsonify({"cases": [case.to_json() for case in cases]}), 201

@case_blueprint.route("case/delete/<id>", methods=['GET'])
@login_required
def delete(id):
    cases = CaseModel.delete(id)
    return jsonify({"message": "delete"}), 201

@case_blueprint.route("/view/<id>", methods=['GET'])
@login_required
def view(id):
    case = CaseModel.get(id)
    print(case)
    if case:
        return render_template("case/case_view.html", id=id, case=case)
    return render_template("404.html")


@case_blueprint.route("/add", methods=['GET','POST'])
@login_required
def add_case():
    form = CaseForm()
    if form.validate_on_submit():
        case = CaseModel.add_case_core(form)
        return redirect(f"/case/view/{case.id}")
    return render_template("case/add_case.html", form=form)


@case_blueprint.route("/add_task/<id>", methods=['GET','POST'])
@login_required
def add_task(id):
    form = TaskForm()
    # form.group_id.choices = [(g.uuid, g.title) for g in Case.query.order_by('title')]
    if form.validate_on_submit():
        task = CaseModel.add_task_core(form, id)
        return redirect(f"/case/view/{id}")
    return render_template("case/add_task.html", form=form)