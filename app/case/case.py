from flask import Blueprint, render_template, redirect, jsonify, request
from .form import CaseForm, TaskForm, CaseEditForm, TaskEditForm
from flask_login import login_required, current_user
from . import case_core as CaseModel

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

@case_blueprint.route("/delete", methods=['POST'])
@login_required
def delete():
    id = request.json["id_case"]
    if CaseModel.delete(id):
        return jsonify({"message": "Case deleted"}), 201
    else:
        return jsonify({"message": "Error case deleted"}), 201

@case_blueprint.route("/view/<id>", methods=['GET'])
@login_required
def view(id):
    case = CaseModel.get(id)
    # print(case)
    if case:
        return render_template("case/case_view.html", id=id, case=case.to_json())
    return render_template("404.html")

@case_blueprint.route("view/get_case_info/<id>", methods=['GET'])
@login_required
def get_case_info(id):
    case = CaseModel.get(id)
    
    tasks = list()
    for task in case.tasks:
        users, flag = CaseModel.get_user_assign_task(task.id)
        task.notes = CaseModel.markdown_notes(task.notes)
        tasks.append((task.to_json(), users, flag))

    case_users = CaseModel.get_user_assign_case(case.id)

    return jsonify({"case": case.to_json(), "tasks": tasks, "case_users": case_users}), 201


@case_blueprint.route("/delete_task", methods=['POST'])
@login_required
def delete_task():
    id = request.json["id_task"]
    if CaseModel.delete_task(id):
        return jsonify({"message": "Task deleted"}), 201
    else:
        return jsonify({"message": "Error task deleted"}), 201


@case_blueprint.route("/add", methods=['GET','POST'])
@login_required
def add_case():
    form = CaseForm()
    if form.validate_on_submit():
        case = CaseModel.add_case_core(form)
        return redirect(f"/case/view/{case.id}")
    return render_template("case/add_case.html", form=form)


@case_blueprint.route("/edit/<id>", methods=['GET','POST'])
@login_required
def edit_case(id):
    form = CaseEditForm()

    if form.validate_on_submit():
        CaseModel.edit_case_core(form, id)
        return redirect(f"/case/view/{id}")
    else:
        case_modif = CaseModel.get(id)
        form.description.data = case_modif.description
        form.title.data = case_modif.title
        form.dead_line_date.data = case_modif.dead_line
        form.dead_line_time.data = case_modif.dead_line
    return render_template("case/add_case.html", form=form)


@case_blueprint.route("/add_task/<id>", methods=['GET','POST'])
@login_required
def add_task(id):
    form = TaskForm()
    # form.group_id.choices = [(g.uuid, g.title) for g in Case.query.order_by('title')]
    if form.validate_on_submit():
        CaseModel.add_task_core(form, id)
        return redirect(f"/case/view/{id}")
    return render_template("case/add_task.html", form=form)


@case_blueprint.route("view/<id_case>/edit_task/<id>", methods=['GET','POST'])
@login_required
def edit_task(id_case, id):
    form = TaskEditForm()

    if form.validate_on_submit():
        CaseModel.edit_task_core(form, id)
        return redirect(f"/case/view/{id_case}")
    else:
        task_modif = CaseModel.get_task(id)
        form.description.data = task_modif.description
        form.title.data = task_modif.title
        form.dead_line_date.data = task_modif.dead_line
        form.dead_line_time.data = task_modif.dead_line
    
    return render_template("case/add_task.html", form=form)


@case_blueprint.route("/modif_note", methods=['POST'])
@login_required
def modif_note():
    id = request.json["id_task"]
    notes = request.json["notes"]
    
    if CaseModel.modif_note_core(id, notes):
        return jsonify({"message": "Note added"}), 201
    else:
        return jsonify({"message": "Error not added"}), 201


@case_blueprint.route("/get_note_text", methods=['GET'])
@login_required
def get_note_text():
    """Get category page"""

    data_dict = dict(request.args)
    note = CaseModel.get_note_text(data_dict["id"])

    return jsonify({"note": note}), 201

@case_blueprint.route("/get_note_markdown", methods=['GET'])
@login_required
def get_note_markdown():
    """Get category page"""

    data_dict = dict(request.args)
    note = CaseModel.get_note_markdown(data_dict["id"])

    return jsonify({"note": note}), 201


@case_blueprint.route("/take_task", methods=['POST'])
@login_required
def take_task():
    """Get category page"""

    id = request.json["task_id"]

    CaseModel.assign_task(id)

    return jsonify({"user": current_user.to_json()}), 201


@case_blueprint.route("/remove_assign_task", methods=['POST'])
@login_required
def remove_assign_task():
    """Get category page"""

    id = request.json["task_id"]

    CaseModel.remove_assign_task(id)

    return jsonify({"user": current_user.to_json()}), 201