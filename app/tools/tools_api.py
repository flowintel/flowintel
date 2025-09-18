from flask import request
from . import tools_core as ToolModel

from flask_restx import Namespace, Resource
from ..decorators import api_required

from ..utils import utils

from . import validate_api as ValidateApi


importer_ns = Namespace("importer", description="Endpoints to manage importer")

    
@importer_ns.route('/case')
@importer_ns.doc(description='Import a case. JSON is required')
class ImportCase(Resource):
    method_decorators = [api_required]
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
            return {"message": "All created"}
        
    
@importer_ns.route('/template')
@importer_ns.doc(description='Import a case template. JSON is required')
class ImportCaseTemplate(Resource):
    method_decorators = [api_required]
    def post(self):
        if request.json:
            current_user = utils.get_user_api(request.headers["X-API-KEY"])
            if type(request.json) == list:
                for case in request.json:
                    res = ToolModel.case_template_creation_from_importer(case, current_user)
                    if res:
                        return res
            else:
                res = ToolModel.case_template_creation_from_importer(request.json, current_user)
                if res:
                    return res
            return {"message": "All created"}
        


case_misp_ns = Namespace("case_misp", description="Endpoints to manage case creation from misp")


@case_misp_ns.route('/')
@case_misp_ns.doc(description='Create a Case from a MISP Event')
class CaseMispEvent(Resource):
    method_decorators = [api_required]
    @case_misp_ns.doc(params={
        "case_title": "Required. Title for the new case",
        "case_template_id": "Required. Id of a case template",
        "misp_instance_id": "Required. Id of a misp instance",
        "misp_event_id": "Required. Id of a misp event on the misp instance"
    })
    def post(self):
        if request.json:
            current_user = utils.get_user_api(request.headers["X-API-KEY"])
            verif_dict = ValidateApi.validate_case_from_misp(request.json, current_user)

            if "message" not in verif_dict:
                case = ToolModel.create_case_misp_event(request.json, current_user)
                return {"message": f"Case created, id: {case.id}", "case_id": case.id}, 201

            return verif_dict, 400
        return {"message": "Please give data"}, 400
    