import datetime
import os
from flask import render_template, request, current_app, abort
from flask_login import login_required, current_user
import requests
import conf.config_module as ConfigModule

from .case import case_blueprint, check_user_private_case
from .CaseCore import CaseModel, FILE_FOLDER
from . import common_core as CommonModel
from ..db_class.db import Case, Case_Link_Case, File, Task_User, User
from ..decorators import editor_required, admin_required
from ..utils.logger import flowintel_log
from ..utils.note_variables import resolve_variables, get_syntax_reference
from ..utils.file_converter import convert_file_to_note_content
from ..utils.gpg import sign_text

@case_blueprint.route("/<cid>/all_notes", methods=['GET'])
@login_required
def all_notes(cid):
    """Get all tasks notes for a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get all notes of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        
        notes = CaseModel.get_all_notes(case)
        flowintel_log("audit", 200, "Get all notes of a case", User=current_user.email, CaseId=cid)
        return {"notes": notes}
    return {"message": "Case Not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_case", methods=['POST'])
@login_required
@editor_required
def modif_note(cid):
    """Modify note of the task"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            notes = request.json["notes"]
            if CaseModel.modify_note_core(cid, current_user, notes):
                flowintel_log("audit", 200, "Note modified", User=current_user.email, CaseId=cid)
                return {"message": "Note modified", "toast_class": "success-subtle"}, 200
            return {"message": "Error add/modify note", "toast_class": "danger-subtle"}, 400
        flowintel_log("audit", 403, "Modify note: Org not assigned to case", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_notes", methods=['GET'])
@login_required
def export_notes(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Export notes of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            res = CommonModel.export_notes(case_task=True, case_task_id=cid, type_req=request.args.get("type"))
            try:
                CommonModel.delete_temp_folder()
            except OSError:
                pass
            if isinstance(res, dict):
                flowintel_log("error", 400, "Export notes of a case failed", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"), ErrorMessage=res.get("message"))
                return res, 400
            flowintel_log("audit", 200, "Export notes of a case", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"))
            return res
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/run_computer_assistate_report", methods=['GET'])
@login_required
@editor_required
def run_computer_assistate_report(cid):
    """Create a report from all case information"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Run computer assisted report: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
            flowintel_log("audit", 403, "Run computer assisted report: Org not assigned to case", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        if not CaseModel.check_exist_task(case.uuid):
            flowintel_log("audit", 200, "Run computer assisted report", User=current_user.email, CaseId=cid)
            model = request.args.get('model') if request.args.get('model') else None
            prompt = request.args.get('prompt') if request.args.get('prompt') else None
            return CaseModel.generate_computer_assistate_report(case, current_user, model=model, prompt=prompt)
        return {"message": "There's already a generation going for this case", "toast_class": "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/status_computer_assistate_report", methods=['GET'])
@login_required
def status_computer_assistate_report(cid):
    """Create a report from all case information"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get status computer assisted report: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if CaseModel.get_status_computer_assistate_report(case.uuid):
            flowintel_log("audit", 200, "Get status computer assisted report", User=current_user.email, CaseId=cid)
            return {"report_status": "running"}, 200
        return {"report_status": "done", "message": "Report generation completed"}, 200
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/get_computer_assistate_report", methods=['GET'])
@login_required
def get_computer_assistate_report(cid):
    """Create a report from all case information"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Get computer assisted report: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403

        flowintel_log("audit", 200, "Get computer assisted report", User=current_user.email, CaseId=cid)

        resp = {"report": case.computer_assistate_report}
        # Include persisted model/prompt if available
        try:
            if getattr(case, 'computer_assistate_model', None):
                resp["model"] = case.computer_assistate_model
            if getattr(case, 'computer_assistate_prompt', None):
                resp["prompt"] = case.computer_assistate_prompt
        except Exception:
            pass
        return resp
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_computer_assistate_report", methods=['GET'])
@login_required
def export_computer_assistate_report(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Export computer assisted report of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            res = CommonModel.export_notes_core(case_task_id=None, 
                                                type_req=request.args.get("type"), 
                                                note=case.computer_assistate_report, 
                                                download_filename=f"case_{case.uuid}_computer_assistate_report")
            try:
                CommonModel.delete_temp_folder()
            except OSError:
                pass
            if isinstance(res, dict):
                return res, 400
            flowintel_log("audit", 200, "Export computer assisted report of a case", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"))
            return res
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/list_ollama_models", methods=['GET'])
@login_required
def list_ollama_models():
    """Return a list of available models from the configured Ollama server"""
    if not ConfigModule.OLLAMA_URL:
        return {"message": "Ollama URL not configured", 'toast_class': "warning-subtle"}, 400

    url = f"{ConfigModule.OLLAMA_URL}/api/tags"
    headers = {}
    if getattr(ConfigModule, 'OLLAMA_KEY', None):
        headers["Authorization"] = f"Bearer {ConfigModule.OLLAMA_KEY}"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        models = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('model') or item.get('id')
                    if name:
                        models.append(name)
                elif isinstance(item, str):
                    models.append(item)
        elif isinstance(data, dict) and 'models' in data and isinstance(data['models'], list):
            for item in data['models']:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('model') or item.get('id')
                    if name:
                        models.append(name)
        flowintel_log("audit", 200, "List ollama models", User=current_user.email)
        return {"models": models}, 200
    except requests.RequestException as e:
        flowintel_log("error", 500, f"Error listing ollama models: {e}", User=current_user.email)
        return {"message": "Unable to reach Ollama", 'toast_class': "danger-subtle"}, 500


@case_blueprint.route("/<cid>/change_hedgedoc_url", methods=['POST'])
@login_required
@editor_required
def change_hedgedoc_url(cid):
    """Change hedgedoc url of the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "hedgedoc_url" in request.json:
                if CaseModel.change_hedgedoc_url(request.json, cid, current_user):
                    flowintel_log("audit", 200, "HedgeDoc URL changed", User=current_user.email, CaseId=cid)
                    return {"message": "HedgeDoc URL updated", "toast_class": "success-subtle"}, 200
                return {"message": "Error updating HedgeDoc URL", "toast_class": "danger-subtle"}, 400
            return {"message": "Need to pass 'hedgedoc_url'", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Change HedgeDoc URL: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404

@case_blueprint.route("/<cid>/get_hedgedoc_notes", methods=['GET'])
@login_required
@editor_required
def get_hedgedoc_notes(cid):
    """Get hedgedoc notes of the case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            flowintel_log("audit", 200, "Get HedgeDoc notes", User=current_user.email, CaseId=cid)
            return CaseModel.get_hedgedoc_notes(cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


#################
# Note Template #
#################

@case_blueprint.route("/<cid>/get_note_template", methods=['GET'])
@login_required
def get_note_template(cid):
    """Get note template of a case"""
    case_note_template = CaseModel.get_case_note_template(cid)
    if case_note_template:
        template = CaseModel.get_note_template_model(case_note_template.note_template_id)
        if not template:
            CaseModel.remove_note_template(cid)
            return {"message": "The linked note template no longer exists and has been unlinked", "toast_class": "warning-subtle"}, 404
        return {"case_note_template": case_note_template.to_json(), "current_template": template.to_json()}, 200
    return {"message": "No note template for the case"}, 404


@case_blueprint.route("/<cid>/create_note_template_case", methods=['POST'])
@login_required
@editor_required
def create_note_template_case(cid):
    """Create note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "values" in request.json and "template_id" in request.json:
                if CaseModel.create_note_template(cid, request.json, current_user):
                    flowintel_log("audit", 200, "Case note template created", User=current_user.email, CaseId=cid, TemplateId=request.json["template_id"])
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "Missing parameters", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Create case note template: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_template_case", methods=['POST'])
@login_required
@editor_required
def modif_note_template_case(cid):
    """Modify note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "values" in request.json:
                if CaseModel.modif_note_template(cid, request.json, current_user):
                    flowintel_log("audit", 200, "Case note template modified", User=current_user.email, CaseId=cid)
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "No values passed", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Modify case note template: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/modif_note_template_content", methods=['POST'])
@login_required
@editor_required
def modif_note_template_content(cid):
    """Modify Content of note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "content" in request.json:
                if CaseModel.modif_content_note_template(cid, request.json, current_user):
                    flowintel_log("audit", 200, "Case note template content modified", User=current_user.email, CaseId=cid)
                    return {"message": "Note template modified successfully", "toast_class": "success-subtle"}, 200
                return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
            return {"message": "No content passed", "toast_class": "warning-subtle"}, 400
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


@case_blueprint.route("/<cid>/export_notes_template", methods=['POST'])
@login_required
def export_notes_template(cid):
    """Export note of a case"""
    case = CommonModel.get_case(cid)
    if case:
        if not check_user_private_case(case):
            flowintel_log("audit", 403, "Export notes template of a case: Private case: Permission denied", User=current_user.email, CaseId=cid)
            return {"message": "Permission denied", 'toast_class': "danger-subtle"}, 403
        if "type" in request.args:
            if "content" in request.json:
                res = CommonModel.export_notes_core(case_task_id=cid, type_req=request.args.get("type"), note=request.json["content"])
                try:
                    CommonModel.delete_temp_folder()
                except OSError:
                    pass
                if isinstance(res, dict):
                    flowintel_log("error", 400, "Export notes template of a case failed", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"), ErrorMessage=res.get("message"))
                    return res, 400
                flowintel_log("audit", 200, "Export notes template of a case", User=current_user.email, CaseId=cid, ExportType=request.args.get("type"))
                return res
            return {"message": "No content passed", "toast_class": "warning-subtle"}, 400
        return {"message": "'type' is missing", 'toast_class': "warning-subtle"}, 400
    return {"message": "Case not found", 'toast_class': "danger-subtle"}, 404


@case_blueprint.route("/<cid>/remove_note_template", methods=['GET'])
@login_required
@editor_required
def remove_note_template(cid):
    """Remove note template of a case"""
    if CommonModel.get_case(cid):
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.remove_note_template(cid):
                flowintel_log("audit", 200, "Case note template removed", User=current_user.email, CaseId=cid)
                return {"message": "Note Template removed", "toast_class": "success-subtle"}, 200
            return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400
        flowintel_log("audit", 403, "Remove case note template: Action not allowed", User=current_user.email, CaseId=cid)
        return {"message": "Action not allowed", "toast_class": "warning-subtle"}, 403
    return {"message": "Case not found", "toast_class": "danger-subtle"}, 404


########
# Report
########

@case_blueprint.route("/<cid>/report", methods=['GET'])
@login_required
@admin_required
def case_report(cid):
    """Render the report builder page for a case"""
    case = CommonModel.get_case(cid)
    if not case:
        abort(404)
    return render_template("case/case_report.html", case=case)


@case_blueprint.route("/<cid>/report/generate", methods=['POST'])
@login_required
@admin_required
def case_report_generate(cid):
    """Generate and return the Markdown report text for a case"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found"}, 404

    def _text_color(hex_color):
        h = (hex_color or '#888888').lstrip('#')
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return 'white'
        return 'white' if (299 * r + 587 * g + 114 * b) / 1000 < 128 else 'black'

    def _tag_badge(name, color):
        tc = _text_color(color or '#888888')
        bg = color or '#888888'
        return f'<span class="tag" style="background-color:{bg};color:{tc};">{name}</span>'

    def _cluster_badge(label):
        return f'<span class="cluster">{label}</span>'

    opts = request.json or {}
    tasks = case.tasks.all()

    try:
        ver_path = os.path.join(current_app.root_path, '..', 'version')
        with open(ver_path) as _vf:
            _version = _vf.read().strip()
    except Exception:
        _version = 'unknown'

    lines = []
    lines.append("# Case report")
    lines.append("")

    main_logo = current_app.config.get('MAIN_LOGO', '')
    topright_logo = current_app.config.get('TOPRIGHT_LOGO', '')
    logo_html = ''
    if main_logo:
        logo_html += f'<img src="{main_logo}" style="height:50px; margin-right:10px;">'
    if topright_logo:
        logo_html += f'<img src="{topright_logo}" style="height:50px; float:right;">'
    if logo_html:
        lines.append(logo_html)
        lines.append("")

    if opts.get("include_metadata", True):
        lines.append("---")
        lines.append("")
        lines.append("## Case information")

        lines.append(f"- **Case ID:** {case.id}")

        created = case.creation_date.strftime('%Y-%m-%d %H:%M') if case.creation_date else "—"
        lines.append(f"- **Date created:** {created}")

        owner_org = CommonModel.get_org(case.owner_org_id)
        lines.append(f"- **Owner:** {owner_org.name if owner_org else '—'}")

        orgs = CommonModel.get_orgs_in_case(case.id)
        if orgs:
            lines.append("- **Organisations:** " + ", ".join(o.name for o in orgs if o))
        else:
            lines.append("- **Organisations:** —")

        linked = Case.query.join(Case_Link_Case, Case_Link_Case.case_id_2 == Case.id)\
                            .filter(Case_Link_Case.case_id_1 == case.id).all()
        if linked:
            lines.append("- **Linked cases:** " + ", ".join(f"{lc.title} (#{lc.id})" for lc in linked))
        else:
            lines.append("- **Linked cases:** —")

        flags = []
        if case.privileged_case:
            flags.append("Privileged")
        if case.is_private:
            flags.append("Private")
        if flags:
            lines.append("- **Flags:** " + ", ".join(flags))

        if case.deadline:
            lines.append(f"- **Deadline:** {case.deadline.strftime('%Y-%m-%d %H:%M')}")
        if case.time_required:
            lines.append(f"- **Time required:** {case.time_required}")
        if case.ticket_id:
            lines.append(f"- **Ticket ID:** {case.ticket_id}")

        case_connectors = CommonModel.get_case_connectors_name(cid)
        if case_connectors:
            lines.append("- **Connectors:** " + ", ".join(case_connectors))

        total = len(tasks)
        done = sum(1 for t in tasks if t.completed)
        pct = int(done / total * 100) if total > 0 else 0
        lines.append(f"- **Completion:** {done}/{total} tasks ({pct}%)")

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        user_label = f"{current_user.first_name} {current_user.last_name} ({current_user.email})"
        lines.append(f"- **Report generated on:** {now} by {user_label}")

        url = f"http://{current_app.config.get('FLASK_URL', '127.0.0.1')}:{current_app.config.get('FLASK_PORT', 7006)}"
        lines.append(f"- **Instance URL:** {url}")
        lines.append(f"- **Instance version:** {_version}")

        lines.append("")

    if opts.get("include_title", True):
        lines.append("---")
        lines.append("")
        lines.append(f"## Case: {case.title}")
        lines.append("")

    if opts.get("include_description", True):
        lines.append("---")
        lines.append("")
        lines.append("### Description")
        desc = (case.description or "—").replace("```", "")
        lines.append("```")
        lines.extend(desc.splitlines())
        lines.append("```")
        lines.append("")

    if opts.get("include_tasks", True):
        lines.append("---")
        lines.append("")
        lines.append("### Tasks")
        if tasks:
            for task in tasks:
                status_mark = "✓" if task.completed else "○"
                lines.append(f"#### [{status_mark}] {task.title}")
                if task.description:
                    lines.append(task.description)
                lines.append("")

                task_status = CommonModel.get_status(task.status_id)
                lines.append(f"- **Status:** {task_status.name if task_status else '—'}")

                user_ids = [tu.user_id for tu in Task_User.query.filter_by(task_id=task.id).all()]
                if user_ids:
                    owners = User.query.filter(User.id.in_(user_ids)).all()
                    owner_str = ", ".join(f"{u.first_name} {u.last_name} ({u.email})" for u in owners)
                    lines.append(f"- **Owner(s):** {owner_str}")
                else:
                    lines.append("- **Owner(s):** —")

                if task.deadline:
                    lines.append(f"- **Deadline:** {task.deadline.strftime('%Y-%m-%d %H:%M')}")
                if task.time_required:
                    lines.append(f"- **Time required:** {task.time_required}")

                task_tags_json = CommonModel.get_task_tags_json(task.id)
                task_clusters = CommonModel.get_task_clusters(task.id)
                task_galaxies = CommonModel.get_task_galaxies(task.id)

                if task_tags_json:
                    badges = " ".join(_tag_badge(t['name'], t['color']) for t in task_tags_json)
                    lines.append(f"- **Tags:** {badges}")
                if task_clusters:
                    badges = " ".join(_cluster_badge(c.tag) for c in task_clusters)
                    lines.append(f"- **Galaxy clusters:** {badges}")
                if task_galaxies:
                    lines.append("- **Galaxies:** " + ", ".join(g.name for g in task_galaxies))

                subtasks = task.subtasks.all()
                if subtasks:
                    lines.append("- **Subtasks:**")
                    for st in subtasks:
                        tick = "✓" if st.completed else "○"
                        lines.append(f"  - [{tick}] {st.description}")

                urls_tools = task.urls_tools.all()
                if urls_tools:
                    lines.append("- **URL/Tools:** " + ", ".join(ut.name for ut in urls_tools if ut.name))

                ext_refs = task.external_references.all()
                if ext_refs:
                    lines.append("- **External references:** " + ", ".join(er.url for er in ext_refs))

                task_connectors = CommonModel.get_task_connectors_name(task.id)
                if task_connectors:
                    lines.append("- **Connectors:** " + ", ".join(task_connectors))

                lines.append("")
        else:
            lines.append("No tasks.")
            lines.append("")

    if opts.get("include_notes", False):
        lines.append("---")
        lines.append("")
        lines.append("### Notes")
        lines.append("")
        has_notes = False

        if case.notes:
            has_notes = True
            lines.append("#### Case note")
            lines.append("")
            resolved_case_note = resolve_variables(case.notes, case_id=case.id)
            lines.append("```")
            lines.extend(line.replace("```", "") for line in resolved_case_note.splitlines())
            lines.append("```")
            lines.append("")

        task_note_sections = CaseModel.get_all_notes(case)
        if task_note_sections:
            has_notes = True
            lines.append("#### Task notes")
            lines.append("")
            for section in task_note_sections:
                section_text = section["text"] if isinstance(section, dict) else section
                task_id = section["task_id"] if isinstance(section, dict) else None
                resolved_section = resolve_variables(section_text, case_id=case.id, task_id=task_id)
                lines.append("```")
                lines.extend(line.replace("```", "") for line in resolved_section.splitlines())
                lines.append("```")
                lines.append("")

        if not has_notes:
            lines.append("No notes.")
            lines.append("")

    if opts.get("include_files", True):
        lines.append("---")
        lines.append("")
        lines.append("### Files")
        lines.append("")

        task_ids = [t.id for t in tasks]
        case_files = File.query.filter_by(case_id=case.id, task_id=None).all()
        task_files = File.query.filter(File.task_id.in_(task_ids)).all() if task_ids else []
        all_files = case_files + task_files

        if all_files:
            task_map = {t.id: t.title for t in tasks}
            lines.append("| Filename | Size | Type | Attached to |")
            lines.append("|---|---|---|---|")
            for f in all_files:
                size = f"{f.file_size:,} B" if f.file_size is not None else "Unknown"
                ftype = f.file_type or "Unknown"
                attached = "Case" if not f.task_id else f"Task: {task_map.get(f.task_id, 'Unknown')}"
                lines.append(f"| {f.name} | {size} | {ftype} | {attached} |")
        else:
            lines.append("No files.")
        lines.append("")

    case_tags_json = CommonModel.get_case_tags_json(cid)

    if opts.get("include_tags", True):
        lines.append("---")
        lines.append("")
        lines.append("### Tags and galaxies")

        if case_tags_json:
            badges = " ".join(_tag_badge(t['name'], t['color']) for t in case_tags_json)
            lines.append(f"**Tags:** {badges}")

        custom_tags = CommonModel.get_case_custom_tags_json(case.id)
        if custom_tags:
            badges = " ".join(_tag_badge(ct['name'], ct['color']) for ct in custom_tags)
            lines.append(f"**Custom tags:** {badges}")

        clusters = CommonModel.get_case_clusters(cid)
        if clusters:
            badges = " ".join(_cluster_badge(c.tag) for c in clusters)
            lines.append(f"**Galaxy clusters:** {badges}")

        lines.append("")

    if opts.get("include_objects", True):
        lines.append("---")
        lines.append("")
        lines.append("### Objects")
        objects = CaseModel.get_misp_object_by_case(cid)
        if objects:
            for obj in objects:
                lines.append(f"#### {obj.name}")
                for attr in obj.attributes:
                    lines.append(f"  - {attr.object_relation}: {attr.value}")
        else:
            lines.append("No objects.")
        lines.append("")

    if opts.get("include_standalone_attributes", True):
        lines.append("---")
        lines.append("")
        lines.append("### Standalone attributes")
        attributes = CaseModel.get_standalone_attributes_by_case(cid)
        if attributes:
            for attr in attributes:
                lines.append(f"- {attr.type}: {attr.value}")
        else:
            lines.append("No standalone attributes.")
        lines.append("")

    if opts.get("include_taxonomies", False):
        lines.append("---")
        lines.append("")
        lines.append("### Appendix — Taxonomies")
        seen_taxo = {}
        for t in case_tags_json:
            name = t['name']
            taxo_name = name.split(":")[0] if ":" in name else name
            seen_taxo.setdefault(taxo_name, []).append(t)
        if seen_taxo:
            for taxo, tag_objs in sorted(seen_taxo.items()):
                lines.append(f"#### {taxo}")
                for t in tag_objs:
                    badge = _tag_badge(t['name'], t['color'])
                    lines.append(f"  - {badge}")
        else:
            lines.append("No taxonomy tags.")
        lines.append("")

    if opts.get("include_audit", False):
        lines.append("---")
        lines.append("")
        lines.append("### Audit logs")
        audit = CommonModel.get_audit_logs(case.id)
        if audit:
            for entry in audit:
                lines.append(f"- {entry}")
        else:
            lines.append("No audit logs found.")
        lines.append("")

    if opts.get("include_timeline", False):
        lines.append("---")
        lines.append("")
        lines.append("### Timeline")
        history = CommonModel.get_history(case.uuid)
        if history:
            for entry in history:
                lines.append(f"- {entry}")
        else:
            lines.append("No history recorded.")
        lines.append("")

    flowintel_log("audit", 200, "Case report generated",
                  User=current_user.email, CaseId=cid,
                  Options=", ".join(k for k, v in opts.items() if v))

    report_text = "\n".join(lines)
    result = {"report": report_text}

    try:
        sig = sign_text(report_text)
    except Exception as e:
        sig = {"error": str(e)}

    if sig and "error" not in sig:
        result["signature"] = sig["signature"]
        result["signed_by"] = sig["signed_by"]
        result["signed_at"] = sig["signed_at"]
    elif sig and "error" in sig:
        result["signature_error"] = sig["error"]

    return result


@case_blueprint.route("/<cid>/report/attach_pdf", methods=['POST'])
@login_required
@admin_required
def case_report_attach_pdf(cid):
    """Save the generated PDF report as a file attached to the case"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

    if 'file' not in request.files or not request.files['file'].filename:
        return {"message": "No PDF provided", "toast_class": "warning-subtle"}, 400

    created_files = CaseModel.add_file_core(case, request.files, current_user)
    if created_files:
        names = ", ".join(f.name for f in created_files)
        flowintel_log("audit", 200, "Case report attached",
                      User=current_user.email, CaseId=cid, Files=names)
        return {"message": "Report attached to case", "toast_class": "success-subtle"}, 200
    return {"message": "Failed to attach PDF", "toast_class": "danger-subtle"}, 400

@case_blueprint.route("/<cid>/convert_case_file_to_note/<fid>", methods=['POST'])
@login_required
@editor_required
def convert_case_file_to_note(cid, fid):
    """Convert a file attached to a case into a case note"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404

    if not (CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin()):
        flowintel_log("audit", 403, "Convert case file to note: Permission denied", User=current_user.email, CaseId=cid, FileId=fid)
        return {"message": "Permission denied", "toast_class": "warning-subtle"}, 403

    file = CommonModel.get_file(fid)
    if not file or file.case_id != int(cid):
        return {"message": "File not found", "toast_class": "danger-subtle"}, 404

    file_extension = os.path.splitext(file.name)[1].lower().lstrip('.')
    if file_extension not in ['txt', 'csv', 'json']:
        return {"message": "Only TXT, CSV, and JSON files can be converted", "toast_class": "warning-subtle"}, 400

    file_path = os.path.join(FILE_FOLDER, file.uuid)
    success, content = convert_file_to_note_content(file_path, file_extension, file.name)

    if not success:
        flowintel_log("audit", 400, "Case file conversion failed", User=current_user.email, CaseId=cid, FileId=fid, FileName=file.name, Error=content)
        return {"message": f"Conversion failed: {content}", "toast_class": "danger-subtle"}, 400

    existing_notes = case.notes or ""
    new_notes = (existing_notes + "\n\n" + content).strip()
    if not CaseModel.modify_note_core(cid, current_user, new_notes):
        return {"message": "Error saving note", "toast_class": "danger-subtle"}, 400
    flowintel_log("audit", 200, "Case file converted to note", User=current_user.email, CaseId=cid, FileId=fid, FileName=file.name)
    return {"message": f"File '{file.name}' converted to note successfully", "toast_class": "success-subtle", "notes": new_notes}, 200


#####################
# Note Variables    #
#####################

@case_blueprint.route("/<cid>/resolve_note_variables", methods=['POST'])
@login_required
def resolve_note_variables(cid):
    """Resolve @-prefixed variable references in note text"""
    case = CommonModel.get_case(cid)
    if not case:
        return {"message": "Case not found", "toast_class": "danger-subtle"}, 404
    if not check_user_private_case(case):
        return {"message": "Permission denied", "toast_class": "danger-subtle"}, 403
    
    text = request.json.get("text", "")
    task_id = request.json.get("task_id", None)
    mark = request.json.get("mark", False)
    
    resolved = resolve_variables(text, case_id=int(cid), task_id=int(task_id) if task_id else None, mark=bool(mark))
    return {"resolved": resolved}, 200


@case_blueprint.route("/note_variables_reference", methods=['GET'])
@login_required
def note_variables_reference():
    """Return the complete syntax reference for note variables"""
    return {"reference": get_syntax_reference()}, 200

