from flask import request
from . import tools_core as ToolModel

from flask_restx import Namespace, Resource
from ..decorators import api_required, importer_required, template_editor_required

from ..utils import utils
from ..utils.logger import flowintel_log

from . import validate_api as ValidateApi


importer_ns = Namespace("importer", description="Endpoints to manage importer")

    
@importer_ns.route('/case')
@importer_ns.doc(description='Import a case. JSON is required')
class ImportCase(Resource):
    method_decorators = [importer_required, api_required]
    def post(self):
        if request.json:
            current_user = utils.get_user_api(request.headers["X-API-KEY"])
            if type(request.json) == list:
                for case in request.json:
                    res = ToolModel.case_creation_from_importer(case, current_user)
                    if res:
                        return res
            else:
                res = ToolModel.case_creation_from_importer(request.json, current_user)
                if res:
                    return res
            flowintel_log("audit", 200, "Case imported via API", User=current_user.email)
            return {"message": "All created"}
        return {"message": "Please give data"}, 400
        
    
@importer_ns.route('/template')
@importer_ns.doc(description='Import a case template. JSON is required')
class ImportCaseTemplate(Resource):
    method_decorators = [template_editor_required, api_required]
    def post(self):
        if request.json:
            current_user = utils.get_user_api(request.headers["X-API-KEY"])
            if type(request.json) == list:
                for case in request.json:
                    res = ToolModel.case_template_creation_from_importer(case)
                    if res:
                        return res
            else:
                res = ToolModel.case_template_creation_from_importer(request.json)
                if res:
                    return res
            flowintel_log("audit", 200, "Template imported via API", User=current_user.email)
            return {"message": "All created"}
        return {"message": "Please give data"}, 400
        


case_misp_ns = Namespace("case_misp", description="Endpoints to manage case creation from misp")


@case_misp_ns.route('/')
@case_misp_ns.doc(description='Create a Case from a MISP Event')
class CaseMispEvent(Resource):
    method_decorators = [api_required]
    @case_misp_ns.doc(params={
        "case_title": "Required. Title for the new case",
        "case_template_id": "Required. Id of a case template",
        "misp_instance_id": "Required. Id of a misp instance",
        "misp_event_id": "Required. Id of a misp event on the misp instance",
        "selected_object_uuids": "Optional. List of MISP object UUIDs to import. Omit to import every object on the event.",
        "selected_attribute_uuids": "Optional. List of MISP attribute UUIDs to include in the attributes note. Only used when 'import_attributes_note' is true; omit to include all attributes.",
        "import_event_info_note": "Optional boolean (default false on the API). Add a task with a note summarising the MISP event (info, orgs, date, threat level, analysis, distribution).",
        "import_attributes_note": "Optional boolean (default false). Add a task with a markdown table of the (selected) individual attributes.",
        "import_misp_reports": "Optional boolean (default false). Attach every MISP event report to the case as a Markdown (.md) file.",
        "import_misp_files": "Optional boolean (default false). Attach every MISP attachment/malware-sample attribute to the case as a file."
    })
    def post(self):
        if request.json:
            current_user = utils.get_user_api(request.headers["X-API-KEY"])
            verif_dict = ValidateApi.validate_case_from_misp(request.json, current_user)

            if "message" not in verif_dict:
                case = ToolModel.create_case_misp_event(request.json, current_user)
                flowintel_log(
                    "audit", 200, "Case created from MISP event via API",
                    User=current_user.email, CaseId=case.id,
                    MispInstanceId=request.json.get("misp_instance_id"),
                    MispEventId=request.json.get("misp_event_id"),
                )
                return {"message": f"Case created, id: {case.id}", "case_id": case.id}, 201

            return verif_dict, 400
        return {"message": "Please give data"}, 400
    