from flask import request

from app.db_class.db import Case, User, File
from .CaseCore import CaseModel
from . import common_core as CommonModel
from .TaskCore import TaskModel
from . import validation_api as CaseModelApi
from ..utils import utils

from flask_restx import Namespace, Resource
from ..decorators import api_required, editor_required

case_ns = Namespace("case", description="Endpoints to manage cases")


def check_user_private_case(case: Case, request_headers, current_user: User = None):
    if not current_user:
        current_user = utils.get_user_from_api(request_headers)
    if case.is_private and not CommonModel.get_present_in_case(case.id, current_user) and not current_user.is_admin():
        return False
    return True

@case_ns.route('/all')
@case_ns.doc(description='Get all cases')
class GetCases(Resource):
    method_decorators = [api_required]
    def get(self):
        user = utils.get_user_from_api(request.headers)
        cases = CommonModel.get_all_cases(user)
        return {"cases": [case.to_json() for case in cases]}, 200

@case_ns.route('/<cid>')
@case_ns.doc(description='Get a case', params={'cid': 'id of a case'})
class GetCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            case_json = case.to_json()
            orgs = CommonModel.get_orgs_in_case(cid)
            case_json["orgs"] = list()
            for org in orgs:
                case_json["orgs"].append({"id": org.id, "uuid": org.uuid, "name": org.name})
            
            return case_json, 200
        return {"message": "Case not found"}, 404

@case_ns.route('/create', methods=['POST'])
@case_ns.doc(description='Create a case')
class CreateCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "title": "Required. Title for a case", 
        "description": "Description of a case", 
        "deadline_date": "Date(%Y-%m-%d)", 
        "deadline_time": "Time(%H-%M)",
        "tags": "list of tags from taxonomies",
        "clusters": "list of tags from galaxies",
        "custom_tags" : "List of custom tags created on the instance",
        "time_required": "Time required to realize the case",
        "is_private": "Specify if a case is private or not. By default a case is public",
        "ticket_id": "Id of a ticket related to the case"
    })
    def post(self):
        user = utils.get_user_from_api(request.headers)

        if request.json:
            verif_dict = CaseModelApi.verif_create_case_task(request.json)

            if "message" not in verif_dict:
                case = CaseModel.create_case(verif_dict, user)
                return {"message": f"Case created, id: {case.id}", "case_id": case.id}, 201

            return verif_dict, 400
        return {"message": "Please give data"}, 400
    

@case_ns.route('/create_with_event', methods=['POST'])
@case_ns.doc(description='Create a case')
class CreateCaseEvent(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "title": "Required. Title for a case", 
        "event": "Required, Json of a misp event",
        "description": "Description of a case", 
        "deadline_date": "Date(%Y-%m-%d)", 
        "deadline_time": "Time(%H-%M)",
        "tags": "list of tags from taxonomies",
        "clusters": "list of tags from galaxies",
        "custom_tags" : "List of custom tags created on the instance",
        "time_required": "Time required to realize the case",
        "is_private": "Specify if a case is private or not. By default a case is public",
        "ticket_id": "Id of a ticket related to the case",
    })
    def post(self):
        user = utils.get_user_from_api(request.headers)

        if request.json:
            verif_dict = CaseModelApi.verif_create_case_task(request.json)

            if "message" not in verif_dict:
                case = CaseModel.create_case_with_event(verif_dict, user)
                return {"message": f"Case created, id: {case.id}", "case_id": case.id}, 201

            return verif_dict, 400
        return {"message": "Please give data"}, 400
    

@case_ns.route('/<cid>/edit', methods=['POST'])
@case_ns.doc(description='Edit a case', params={'id': 'id of a case'})
class EditCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"title": "Title for a case", 
                     "description": "Description of a case", 
                     "deadline_date": "Date(%Y-%m-%d)", 
                     "deadline_time": "Time(%H-%M)",
                     "tags": "list of tags from taxonomies",
                     "clusters": "list of tags from galaxies",
                     "custom_tags" : "List of custom tags created on the instance",
                     "is_private": "Specify if a case is private or not. By default a case is public",
                     "ticket_id": "Id of a ticket related to the case"
                    })
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if not check_user_private_case(case, request.headers, current_user):
                return {"message": "Permission denied"}, 403
            
            if CommonModel.get_present_in_case(case.id, current_user) or current_user.is_admin():
                if request.json:
                    verif_dict = CaseModelApi.verif_edit_case(request.json, cid)

                    if "message" not in verif_dict:
                        CaseModel.edit(verif_dict, cid, current_user)
                        CaseModel.edit_tags(verif_dict, cid, current_user)
                        return {"message": f"Case {cid} edited"}, 200

                    return verif_dict, 400
                return {"message": "Please give data"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404
    
@case_ns.route('/<cid>/fork', methods=['POST'])
@case_ns.doc(description='Fork a case', params={'cid': 'id of a case'})
class ForkCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "case_title_fork": "Required. Title for the case"
    })
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if not check_user_private_case(case, request.headers, current_user):
                return {"message": "Permission denied"}, 403
            
            if request.json:
                if "case_title_fork" in request.json:
                    new_case = CaseModel.fork_case_core(cid, request.json["case_title_fork"], current_user)
                    if type(new_case) == dict:
                        return new_case, 400
                    return {"new_case_id": new_case.id}, 201
                return {"message": "Need to pass 'case_title_fork'"}, 400
            return {"message": "Please give data"}, 400
        return {"message": "Case not found"}, 404
    
@case_ns.route('/<cid>/merge/<ocid>', methods=['GET'])
@case_ns.doc(description='Merge a case', params={'cid': 'id of the case to merge', 'ocid': 'id of the case to merge in'})
class MergeCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, ocid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if not check_user_private_case(case, request.headers, current_user):
                return {"message": "Permission denied"}, 403
            
            merging_case = CommonModel.get_case(ocid)
            if merging_case and not check_user_private_case(merging_case, request.headers, current_user):
                return {"message": "Permission denied"}, 403
            
            if CaseModel.merge_case_core(case, merging_case, current_user):
                CaseModel.delete_case(cid, current_user)
                return {"message": "Case is merged"}, 200
            return {"message": "Error Merging"}, 400
        return {"message": "Case not found"}, 404

@case_ns.route('/not_completed')
@case_ns.doc(description='Get all not completed cases')
class GetCasesNotCompleted(Resource):
    method_decorators = [api_required]
    def get(self):
        current_user = utils.get_user_from_api(request.headers)
        cases = CommonModel.get_case_by_completed(False, current_user)
        return {"cases": [case.to_json() for case in cases]}, 200
    
@case_ns.route('/completed')
@case_ns.doc(description='Get all completed cases')
class GetCasesCompleted(Resource):
    method_decorators = [api_required]
    def get(self):
        current_user = utils.get_user_from_api(request.headers)
        cases = CommonModel.get_case_by_completed(True, current_user)
        return {"cases": [case.to_json() for case in cases]}, 200    
    
@case_ns.route('/title', methods=["POST"])
@case_ns.doc(description='Get a case by title')
class GetCaseTitle(Resource):
    method_decorators = [api_required]
    @case_ns.doc(params={"title": "Title of a case"})
    def post(self):
        if "title" in request.json:
            current_user = utils.get_user_from_api(request.headers)
            case = CommonModel.get_case_by_title(request.json["title"], current_user)
            if case:
                case_json = case.to_json()
                orgs = CommonModel.get_orgs_in_case(case.id)
                case_json["orgs"] = [{"id": org.id, "uuid": org.uuid, "name": org.name} for org in orgs]            
                return case_json, 200
            return {"message": "Case not found"}, 404
        return {"message": "Need to pass a title"}, 404
    
@case_ns.route('/<cid>/complete')
@case_ns.doc(description='Complete a case', params={'cid': 'id of a case'})
class CompleteCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            case = CommonModel.get_case(cid)
            if case:
                if CaseModel.complete_case(cid, current_user):
                    return {"message": f"Case {cid} completed"}, 200
                return {"message": f"Error case {cid} completed"}, 400
            return {"message": "Case not found"}, 404
        return {"message": "Permission denied"}, 403

@case_ns.route('/<cid>/delete')
@case_ns.doc(description='Delete a case', params={'cid': 'id of a case'})
class DeleteCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_case(cid, current_user):
                return {"message": "Case deleted"}, 200
            return {"message": "Error case deleted"}, 400
        return {"message": "Permission denied"}, 403
    
@case_ns.route('/<cid>/add_org', methods=['POST'])
@case_ns.doc(description='Add an org to the case', params={'cid': 'id of a case'})
class AddOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"name": "Name of the organisation", "oid": "id of the organisation"})
    def post(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if "name" in request.json:
                org = CommonModel.get_org_by_name(request.json["name"])
            elif "oid" in request.json:
                org = CommonModel.get_org(request.json["oid"])
            else:
                return {"message": "Required an id or a name of an Org"}, 400

            if org:
                if not CommonModel.get_org_in_case(org.id, cid):
                    if CaseModel.add_orgs_case({"org_id": [org.id]}, cid, current_user):
                        return {"message": f"Org added to case {cid}"}, 200
                    return {"message": f"Error Org added to case {cid}"}, 400
                return {"message": "Org already in case"}, 400
            return {"message": "Org not found"}, 404
        return {"message": "Permission denied"}, 403


@case_ns.route('/<cid>/remove_org/<oid>', methods=['GET'])
@case_ns.doc(description='Add an org to the case', params={'cid': 'id of a case', "oid": "id of an org"})
class RemoveOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, oid):
        current_user = utils.get_user_from_api(request.headers)
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            org = CommonModel.get_org(oid)

            if org:
                if CommonModel.get_org_in_case(org.id, cid):
                    if CaseModel.remove_org_case(cid, org.id, current_user):
                        return {"message": f"Org deleted from case {cid}"}, 200
                    return {"message": f"Error Org deleted from case {cid}"}, 400
                return {"message": "Org not in case"}, 404
            return {"message": "Org not found"}, 404
        return {"message": "Permission denied"}, 403
    
@case_ns.route('/<cid>/history', methods=['GET'])
@case_ns.doc(description='Get history of a case', params={'cid': 'id of a case'})
class History(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            history = CommonModel.get_history(case.uuid)
            if history:
                return {"history": history}, 200
            return {"history": None}, 200
        return {"message": "Case Not found"}, 404

@case_ns.route('/<cid>/create_template', methods=["POST"])
@case_ns.doc(description='Create a template form case', params={'cid': 'id of a case'})
class CreateTemplate(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"title_template": "Title for the template that will be create"})
    def post(self, cid):
        if "title_template" in request.json:
            case = CommonModel.get_case(cid)
            if case:
                current_user = utils.get_user_from_api(request.headers)
                if not check_user_private_case(case, request.headers, current_user):
                    return {"message": "Permission denied"}, 403
                new_template = CaseModel.create_template_from_case(cid, request.json["title_template"], current_user)
                if type(new_template) == dict:
                    return new_template
                return {"template_id": new_template.id}, 201
            return {"message": "Case not found"}, 404
        return {"message": "'title_template' is missing"}, 400


@case_ns.route('/<cid>/recurring', methods=['POST'])
@case_ns.doc(description='Set a case recurring')
class RecurringCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "once": "Date(%Y-%m-%d)", 
        "daily": "Boolean", 
        "weekly": "Date(%Y-%m-%d). Start date.", 
        "monthly": "Date(%Y-%m-%d). Start date.",
        "remove": "Boolean"
    })
    def post(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                verif_dict = CaseModelApi.verif_set_recurring(request.json)

                if "message" not in verif_dict:
                    CaseModel.change_recurring(verif_dict, cid, current_user)
                    return {"message": "Recurring changed"}, 200
                return verif_dict
            return {"message": "Please give data"}, 400
        return {"message": "Permission denied"}, 403


@case_ns.route('/search', methods=['POST'])
@case_ns.doc(description='Get cases matching search terms')
class SearchCase(Resource):
    method_decorators = [api_required]
    @case_ns.doc(params={
        "search": "Required. Search terms"
    })
    def post(self):
        if "search" in request.json:
            current_user = utils.get_user_from_api(request.headers)
            cases = CommonModel.search(request.json["search"], current_user)
            if cases:
                return {"cases": [case.to_json() for case in cases]}, 200
            return {"message": "No case", 'toast_class': "danger-subtle"}, 404
        return {"message": "Please enter terms"}, 400
    
@case_ns.route('/<cid>/change_status', methods=['POST'])
@case_ns.doc(description='Change the status of the case')
class ChangeStatusCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "status_id": "Required. Status id"
    })
    def post(self, cid):
        if "status_id" in request.json:
            case = CommonModel.get_case(cid)
            if case:
                current_user = utils.get_user_from_api(request.headers)
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    CaseModel.change_status_core(request.json["status_id"], case, current_user)
                    return {"message": "Status changed"}, 200
                return {"message": "Permission denied"}, 403
            return {"message": "Case doesn't exist"}, 404
        return {"message": "Please enter a status id"}, 400
    

@case_ns.route('/check_case_title_exist', methods=['POST'])
@case_ns.doc(description='Check if a case with the title exist', params={'title': 'title of a case'})
class CheckTitle(Resource):
    method_decorators = [api_required]
    @case_ns.doc(params={
        'title': 'Required. Title of a case'
    })
    def post(self):
        if "title" in request.json:
            if CommonModel.check_case_title(request.json["title"]):
                return {"title_already_exist": True}, 200
            return {"title_already_exist": False}, 200
        return {"message": "Please give 'title'"}, 400
    

@case_ns.route('/get_taxonomies', methods=['GET'])
@case_ns.doc(description='Get all taxonomies')
class GetTaxonomies(Resource):
    method_decorators = [api_required]
    def get(self):
        return {"taxonomies": CommonModel.get_taxonomies()}, 200
    
@case_ns.route('/get_tags', methods=['POST'])
@case_ns.doc(description='Get all tags by given taxonomies')
class GetTags(Resource):
    method_decorators = [api_required]
    @case_ns.doc(params={
        'taxonomies': 'Required. List of taxonomies'
    })
    def post(self):
        if "taxonomies" in request.json:
            taxos = request.json["taxonomies"]
            return {"tags": CommonModel.get_tags(taxos)}, 200
        return {"message": "Please give 'taxonomies'"}, 400
    
@case_ns.route('/get_taxonomies_case/<cid>', methods=['GET'])
@case_ns.doc(description='Get all tags and taxonomies in a case')
class GetTaxonomiesCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            tags = CommonModel.get_case_tags(case.id)
            taxonomies = []
            if tags:
                taxonomies = [tag.split(":")[0] for tag in tags]
            return {"tags": tags, "taxonomies": taxonomies}, 200
        return {"message": "Case Not found"}, 404

@case_ns.route('/get_galaxies', methods=['GET'])
@case_ns.doc(description='Get all galaxies')
class GetGalaxies(Resource):
    method_decorators = [api_required]
    def get(self):
        return {"galaxies": CommonModel.get_galaxies()}, 200

@case_ns.route('/get_galaxies_case/<cid>', methods=['GET'])
@case_ns.doc(description='Get all tags and galaxies in a case', params={'galaxies': 'List of galaxies'})
class GetGalaxiesCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            clusters = CommonModel.get_case_clusters(case.id)
            galaxies = []
            if clusters:
                for cluster in clusters:
                    loc_g = CommonModel.get_galaxy(cluster.galaxy_id)
                    if not loc_g.name in galaxies:
                        galaxies.append(loc_g.name)
                    index = clusters.index(cluster)
                    clusters[index] = cluster.tag
            return {"clusters": clusters, "galaxies": galaxies}, 200
        return {"message": "Case Not found"}, 404
    


@case_ns.route('/get_modules', methods=['GET'])
@case_ns.doc(description='Get all modules')
class GetModules(Resource):
    method_decorators = [api_required]
    def get(self):
        return {"modules": CaseModel.get_modules()}, 200

@case_ns.route('/<cid>/get_instance_module', methods=['GET'])
@case_ns.doc(description='Get all instances for a module', params={'module': 'Name of the module to use', "type": "type of the module"})
class GetInstanceModules(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            if "module" in request.args:
                module = request.args.get("module")
            if "type" in request.args:
                type_module = request.args.get("type")
            else:
                return{"message": "Module type error"}, 400
            return {"instances": CaseModel.get_instance_module_core(module, type_module, case.id, current_user.id)}, 200
        return {"message": "Case Not found"}, 404
    

@case_ns.route('/<cid>/call_module_case', methods=['POST'])
@case_ns.doc(description='Call a module on a case')
class CallModuleCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "module": "Required. Name of the module to call",
        "instance_id": "Required. List of name or id of instances to use for the module"
    })
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "module" in request.json:
                    if "instance_id" in request.json:
                        res = CaseModel.call_module_case(request.json["module"], request.json["instance_id"], case, current_user)
                        if res:
                            return res, 400
                        return {"message": "Connector used"}, 200
                    return {"message": "Please give 'instance_id''"}, 400
                return {"message": "Please enter a 'module''"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    

@case_ns.route('/<cid>/get_note')
@case_ns.doc(description='Get note of a case', params={'cid': 'id of a case'})
class GetNote(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            return {"note": case.notes}
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/get_all_users', methods=['GET'])
@case_ns.doc(description='Get list of user that can be assign', params={'cid': 'id of a case'})
class GetAllUsers(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers, current_user):
                return {"message": "Permission denied"}, 403
            users_list = list()
            for org in CommonModel.get_all_org_case(case):
                for user in org.users:
                    if not user == current_user:
                        users_list.append(user.to_json())
            return {"users": users_list}, 200
        return {"message": "Case not found"}, 404

@case_ns.route('/list_status', methods=['GET'])
@case_ns.doc(description='List all status')
class ListStatus(Resource):
    method_decorators = [api_required]
    def get(self):
        return [status.to_json() for status in CommonModel.get_all_status()], 200
    

##############
# Connectors #
##############

@case_ns.route('/get_connectors', methods=['GET'])
@case_ns.doc(description='Get all connectors and instances')
class GetConnectors(Resource):
    method_decorators = [api_required]
    def get(self):
        current_user = utils.get_user_from_api(request.headers)
        connectors_list = CommonModel.get_connectors()
        connectors_dict = dict()
        for connector in connectors_list:
            loc = list()
            for instance in connector.instances:
                if CommonModel.get_user_instance_both(user_id=current_user.id, instance_id=instance.id):
                    loc.append(instance.to_json())
            if loc:
                connectors_dict[connector.name] = loc
        return {"connectors": connectors_dict}, 200
    
@case_ns.route('/get_case_connectors/<cid>', methods=['GET'])
@case_ns.doc(description='Get all connectors instance for a case')
class GetConnectorsCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            instance_list = []
            for case_instance in CommonModel.get_case_connectors(case.id, utils.get_user_from_api(request.headers)):
                loc_instance = CommonModel.get_instance(case_instance.instance_id)
                instance_list.append({
                    "id": loc_instance.id,
                    "name": loc_instance.name,
                    "identifier": case_instance.identifier
                })
            return {"connectors": instance_list}, 200
        return {"message": "Case Not found"}, 404
    
@case_ns.route('/<cid>/add_connectors', methods=['POST'])
@case_ns.doc(description='Add connectors to a case')
class AddConnectorsCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "connectors": "Required. List of connectors instance. Dict with 'name' and 'identifier' as keys."
    })
    def post(self, cid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "connectors" in request.json:
                    if CaseModel.add_connector(cid, request.json, current_user):
                        return {"message": "Connector added"}, 200
                    return {"message": "Error Connector added"}, 400
                return {"message": "Please give a list of connectors"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    
@case_ns.route('/<cid>/edit_connector/<ciid>', methods=['POST'])
@case_ns.doc(description='Edit connector')
class EditConnectorsCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "identifier": "Required. Identifier used by modules to identify where to send data."
    })
    def post(self, cid, ciid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "identifier" in request.json:
                    if CaseModel.edit_connector(ciid, request.json):
                        return {"message": "Connector edited"}, 200
                    return {"message": "Error Connector edited"}, 400
                return {"message": "Please give a list of connectors"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    
@case_ns.route('/<cid>/remove_connector/<ciid>', methods=['GET'])
@case_ns.doc(description='Remove a connector')
class RemoveConnectors(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, ciid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if CaseModel.remove_connector(ciid):
                    return {"message": "Connector removed"}, 200
                return {"message": "Error Connector removed"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    

#################
# Note Template #
#################

@case_ns.route('/<cid>/add_note_template', methods=['GET'])
@case_ns.doc(description='Add a note template to a case')
class AddNoteTemplate(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"note_template_id": "Id of a note template."})
    def get(self, cid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                note_template_id = request.args.get('note_template_id', type=int)
                if CaseModel.create_note_template(cid, {"template_id": note_template_id, "values": {}}, current_user):
                    return {"message": "Note template added to case"}, 200
                return {"message": "Something went wrong"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    

@case_ns.route('/<cid>/get_note_template', methods=['GET'])
@case_ns.doc(description='Get a note template to a case')
class GetNoteTemplate(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        if CommonModel.get_case(cid):
            c = CaseModel.get_case_note_template(cid)
            if c:
                return c.to_json(), 200
            return {"message": "Case have no note template"}, 404
        return {"message": "Case doesn't exist"}, 404
    
@case_ns.route('/<cid>/modif_values_note_template', methods=['POST'])
@case_ns.doc(description='Modify values of note template of a case', params={'cid': 'id of a case'})
class ModifValuesNoteTemplateCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"values": "Dictionnary with values"})
    def post(self, cid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "values" in request.json:
                    if CaseModel.modif_note_template(cid, request.json, current_user):
                        return {"message": f"Note Template for Case {cid} edited"}, 200
                    return {"message": f"Error Note Template for Case {cid} edited"}, 400
                return {"message": "Key 'values' not found"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/modif_content_note_template', methods=['POST'])
@case_ns.doc(description='Modify content of note template of a case', params={'cid': 'id of a case'})
class ModifContentNoteTemplateCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"content": "Content modify of the note template"})
    def post(self, cid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "content" in request.json:
                    if CaseModel.modif_content_note_template(cid, request.json, current_user):
                        return {"message": f"Note Template for Case {cid} edited"}, 200
                    return {"message": f"Error Note Template for Case {cid} edited"}, 400
                return {"message": "Key 'content' not found"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404   
    

@case_ns.route('/<cid>/remove_note_template', methods=['GET'])
@case_ns.doc(description='Remove note template from a case')
class RemoveNoteTemplate(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"note_template_id": "Id of a note template."})
    def get(self, cid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if CaseModel.remove_note_template(cid):
                    return {"message": "Note template removed"}, 200
                return {"message": "Something went wrong"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404

#########
# Tasks #
#########

@case_ns.route('/<cid>/tasks')
@case_ns.doc(description='Get all tasks for a case', params={'cid': 'id of a case'})
class GetTasks(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            tasks = list()
            for task in case.tasks:
                if not task.completed:
                    tasks.append(task.to_json())

            return tasks, 200
        return {"message": "Case not found"}, 404
    

@case_ns.route('/<cid>/tasks_finished')
@case_ns.doc(description='Get all tasks for a case', params={'cid': 'id of a case'})
class GetTasksFinished(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            tasks = list()
            for task in case.tasks:
                if task.completed:
                    tasks.append(task.to_json())

            return tasks, 200
        return {"message": "Case not found"}, 404
    

@case_ns.route('/<cid>/create_task', methods=['POST'])
@case_ns.doc(description='Create a new task to a case', params={'cid': 'id of a case'})
class CreateTask(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={
        "title": "Required. Title for a task", 
        "description": "Description of a task",
        "deadline_date": "Date(%Y-%m-%d)", 
        "deadline_time": "Time(%H-%M)",
        "tags": "list of tags from taxonomies",
        "clusters": "list of tags from galaxies",
        "galaxies": "list of galaxies name",
        "identifier": "Dictionnary with connector as key and identifier as value",
        "custom_tags" : "List of custom tags created on the instance",
        "time_required": "Time required to realize the task"
    })
    def post(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                verif_dict = CaseModelApi.verif_create_case_task(request.json)

                if "message" not in verif_dict:
                    task = TaskModel.create_task(verif_dict, cid, current_user)
                    return {"message": f"Task {task.id} created for case id: {cid}", "task_id": task.id}, 201
                return verif_dict, 400
            return {"message": "Please give data"}, 400
        return {"message": "Permission denied"}, 403    

@case_ns.route('/<cid>/change_order/<tid>', methods=['POST'])
@case_ns.doc(description='Change the order of the task', params={"cid": "id of a case", "tid": "id of a task"})
class ChangeOrder(Resource):
    method_decorators = [editor_required, api_required]
    def post(self, cid, tid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                task = CommonModel.get_task(tid)
                if task:
                    if 'new-index' in request.json:
                        request.json['new-index'] = request.json['new-index']-1
                        if TaskModel.change_order(case, task, request.json):
                            return {"message": "Order changed"}, 200
                        return {"message": "New index is not one of an other task"}, 400
                    return {"message": "'new-index' need to be passed"}, 400
                return {"message": "Task Not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Case Not found"}, 404
    

@case_ns.route('/<cid>/all_notes')
@case_ns.doc(description='Get all notes of a case', params={'cid': 'id of a case'})
class GetAllNotes(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            return {"notes": CaseModel.get_all_notes(case)}
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/modify_case_note', methods=['POST'])
@case_ns.doc(description='Edit note of a case', params={'cid': 'id of a case'})
class ModifNoteCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"note": "note to create or modify"})
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "note" in request.json:
                    if CaseModel.modify_note_core(cid, current_user, request.json["note"]):
                        return {"message": f"Note for Case {cid} edited"}, 200
                    return {"message": f"Error Note for Case {cid} edited"}, 400
                return {"message": "Key 'note' not found"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404

    ###############
    # MISP Object #
    ###############

    @case_ns.route('/<cid>/get_case_misp_object', methods=['GET'])
    @case_ns.doc(description='Get case list of misp object')
    class GetCaseMispObject(Resource):
        method_decorators = [api_required]
        def get(self, cid):
            case = CommonModel.get_case(cid)
            if case:
                current_user = utils.get_user_from_api(request.headers)
                if not check_user_private_case(case, request.headers, current_user):
                    return {"message": "Permission denied"}, 403

                misp_object = CaseModel.get_misp_object_by_case(cid)
                loc_object = list()
                for obj in misp_object:
                    loc_attr_list = list()
                    for attribute in obj.attributes:
                        res = CaseModel.check_correlation_attr(cid, attribute)
                        loc_attr = attribute.to_json()
                        loc_attr["correlation_list"] = res
                        loc_attr_list.append(loc_attr)

                    loc_object.append({
                        "object_name": obj.name,
                        "attributes": loc_attr_list,
                        "object_id": obj.id,
                        "object_uuid": obj.template_uuid,
                        "object_creation_date": obj.creation_date.strftime('%Y-%m-%d %H:%M') if obj.creation_date else None,
                        "object_last_modif": obj.last_modif.strftime('%Y-%m-%d %H:%M') if obj.last_modif else None
                    })

                return {"misp-object": loc_object}, 200
            return {"message": "Case not found"}, 404


    @case_ns.route('/<cid>/get_correlation_attr/<aid>', methods=['GET'])
    @case_ns.doc(description='Get correlation list for an attribute')
    class GetCorrelationAttr(Resource):
        method_decorators = [api_required]
        def get(self, cid, aid):
            attribute = CaseModel.get_misp_attribute(aid)
            res = CaseModel.check_correlation_attr(cid, attribute)
            return {"correlation_list": res}, 200


    @case_ns.route('/get_misp_object', methods=['GET'])
    @case_ns.doc(description='Get list of misp object templates')
    class GetMispObjectTemplates(Resource):
        method_decorators = [api_required]
        def get(self):
            return {"misp-object": utils.get_object_templates()}, 200


    @case_ns.route('/<cid>/create_misp_object', methods=['POST'])
    @case_ns.doc(description='Create misp object')
    class CreateMispObject(Resource):
        method_decorators = [editor_required, api_required]
        def post(self, cid):
            if CommonModel.get_case(cid):
                current_user = utils.get_user_from_api(request.headers)
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if request.json:
                        if "object-template" in request.json:
                            if "attributes" in request.json:
                                CaseModel.create_misp_object(cid, request.json, current_user)
                                return {"message": "Object created"}, 200
                            return {"message": "Need to pass 'attributes'"}, 400
                        return {"message": "Need to pass 'object-template'"}, 400
                    return {"message": "Please give data"}, 400
                return {"message": "Permission denied"}, 403
            return {"message": "Case not found"}, 404


    @case_ns.route('/<cid>/delete_object/<oid>', methods=['GET'])
    @case_ns.doc(description='Delete an object from case')
    class DeleteMispObject(Resource):
        method_decorators = [editor_required, api_required]
        def get(self, cid, oid):
            if CommonModel.get_case(cid):
                current_user = utils.get_user_from_api(request.headers)
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if CaseModel.delete_object(cid, oid, current_user):
                        return {"message": "Object deleted"}, 200
                    return {"message": "Object not found in this case"}, 404
                return {"message": "Permission denied"}, 403
            return {"message": "Case not found"}, 404


    @case_ns.route('/<cid>/add_attributes/<oid>', methods=['POST'])
    @case_ns.doc(description='Add attributes to an existing object')
    class AddAttributes(Resource):
        method_decorators = [editor_required, api_required]
        def post(self, cid, oid):
            if CommonModel.get_case(cid):
                current_user = utils.get_user_from_api(request.headers)
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if request.json:
                        if "object-template" in request.json:
                            if "attributes" in request.json:
                                if CaseModel.add_attributes_object(cid, oid, request.json):
                                    return {"message": "Receive"}, 200
                                return {"message": "Object not found in this case"}, 404
                            return {"message": "Need to pass 'attributes'"}, 400
                        return {"message": "Need to pass 'object-template'"}, 400
                    return {"message": "Please give data"}, 400
                return {"message": "Permission denied"}, 403
            return {"message": "Case not found"}, 404


    @case_ns.route('/<cid>/misp_object/<oid>/edit_attr/<aid>', methods=['POST'])
    @case_ns.doc(description='Edit misp object attribute')
    class EditMispAttr(Resource):
        method_decorators = [editor_required, api_required]
        def post(self, cid, oid, aid):
            if CommonModel.get_case(cid):
                current_user = utils.get_user_from_api(request.headers)
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    if request.json:
                        if "value" in request.json and "type" in request.json:
                            return CaseModel.edit_attr(cid, oid, aid, request.json)
                        if "type" not in request.json:
                            return {"message": "Need to pass 'type'"}, 400
                        return {"message": "Need to pass 'value'"}, 400
                    return {"message": "Please give data"}, 400
                return {"message": "Permission denied"}, 403
            return {"message": "Case not found"}, 404


    @case_ns.route('/<cid>/misp_object/<oid>/delete_attribute/<aid>', methods=['GET'])
    @case_ns.doc(description='Delete an attribute from a misp object')
    class DeleteMispAttr(Resource):
        method_decorators = [editor_required, api_required]
        def get(self, cid, oid, aid):
            if CommonModel.get_case(cid):
                current_user = utils.get_user_from_api(request.headers)
                if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    return CaseModel.delete_attribute(cid, oid, aid)
                return {"message": "Permission denied"}, 403
            return {"message": "Case not found"}, 404

    

@case_ns.route('/<cid>/append_case_note', methods=['POST'])
@case_ns.doc(description='Append notes to a case', params={'cid': 'id of a case'})
class AppendNoteCase(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={"note": "note to create or modify"})
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "note" in request.json:
                    if CaseModel.append_note_core(cid, current_user, request.json["note"]):
                        return {"message": f"Note for Case {cid} edited"}, 200
                    return {"message": f"Error Note for Case {cid} edited"}, 400
                return {"message": "Key 'note' not found"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/files')
@case_ns.doc(description='Get list of files for a case', params={"cid": "id of a case"})
class GetCaseFiles(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            if not check_user_private_case(case, request.headers):
                return {"message": "Permission denied"}, 403
            
            try:
                file_list = [file.to_json() for file in case.files]
            except Exception:
                file_list = []
            return {"files": file_list}, 200
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/upload_file')
@case_ns.doc(description='Upload a file to a case')
class UploadCaseFile(Resource):
    method_decorators = [editor_required, api_required]
    @case_ns.doc(params={})
    def post(self, cid):
        from ..utils.utils import validate_file_size
        from ..utils.logger import flowintel_log
        
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                files_list = request.files
                has_files = any(files_list[key].filename for key in files_list)
                if has_files:
                    # Validate file sizes before processing
                    for file_key in files_list:
                        file_obj = files_list[file_key]
                        if file_obj.filename:
                            is_valid, error_msg, file_size_mb = validate_file_size(file_obj)
                            if not is_valid:
                                flowintel_log("audit", 400, "API: Add files to case: File size too large", User=current_user.email, CaseId=cid, FileName=file_obj.filename, FileSizeMB=file_size_mb)
                                return {"message": error_msg}, 400
                    
                    # Reset 
                    for file_key in files_list:
                        if files_list[file_key].filename:
                            files_list[file_key].seek(0)
                    
                    created_files = CaseModel.add_file_core(case, files_list, current_user)
                    if created_files:
                        file_details = [f"{f.name} ({f.file_size} bytes, {f.file_type})" for f in created_files]
                        flowintel_log("audit", 200, "API: Files added to case", User=current_user.email, CaseId=cid, FilesCount=len(created_files), Files="; ".join(file_details))
                        return {"message": "File(s) added"}, 200
                    return {"message": "Error adding file(s)"}, 400
                return {"message": "No files provided"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/download_file/<fid>')
@case_ns.doc(description='Download a file from a case', params={"cid": "id of a case", "fid": "id of a file"})
class DownloadCaseFile(Resource):
    method_decorators = [api_required]
    def get(self, cid, fid):
        from ..utils.logger import flowintel_log
        
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                file = File.query.get(fid)
                if file and file.case_id == int(cid):
                    flowintel_log("audit", 200, "API: File downloaded from case", User=current_user.email, CaseId=cid, FileId=fid, FileName=file.name)
                    return CaseModel.download_file(file)
                return {"message": "File not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404


@case_ns.route('/<cid>/delete_file/<fid>')
@case_ns.doc(description='Delete a file from a case', params={"cid": "id of a case", "fid": "id of a file"})
class DeleteCaseFile(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, fid):
        from ..utils.logger import flowintel_log
        
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CommonModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                file = File.query.get(fid)
                if file and file.case_id == int(cid):
                    file_name = file.name
                    file_size = file.file_size if file.file_size else 0
                    file_type = file.file_type if file.file_type else "unknown"
                    
                    if CaseModel.delete_file(file, case, current_user):
                        flowintel_log("audit", 200, "API: Case file deleted", User=current_user.email, CaseId=cid, FileId=fid, FileName=file_name, FileSize=f"{file_size} bytes", FileType=file_type)
                        return {"message": "File deleted"}, 200
                    return {"message": "Error deleting file"}, 400
                return {"message": "File not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404