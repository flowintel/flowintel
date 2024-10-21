from flask import Blueprint, request
from . import case_core as CaseModel
from . import common_core as CommonModel
from . import task_core as TaskModel
from . import case_core_api as CaseModelApi
from ..utils import utils

from flask_restx import Api, Resource
from ..decorators import api_required, editor_required

api_case_blueprint = Blueprint('api_case', __name__)
api = Api(api_case_blueprint,
        title='flowintel API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic flowintel API', 
        doc='/doc/'
    )



@api.route('/all')
@api.doc(description='Get all cases')
class GetCases(Resource):
    method_decorators = [api_required]
    def get(self):
        cases = CommonModel.get_all_cases()
        return {"cases": [case.to_json() for case in cases]}, 200

@api.route('/<cid>')
@api.doc(description='Get a case', params={'cid': 'id of a case'})
class GetCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            case_json = case.to_json()
            orgs = CommonModel.get_orgs_in_case(cid)
            case_json["orgs"] = list()
            for org in orgs:
                case_json["orgs"].append({"id": org.id, "uuid": org.uuid, "name": org.name})
            
            return case_json, 200
        return {"message": "Case not found"}, 404

@api.route('/create', methods=['POST'])
@api.doc(description='Create a case')
class CreateCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "title": "Required. Title for a case", 
        "description": "Description of a case", 
        "deadline_date": "Date(%Y-%m-%d)", 
        "deadline_time": "Time(%H-%M)",
        "tags": "list of tags from taxonomies",
        "clusters": "list of tags from galaxies",
        "identifier": "Dictionnary with connector as key and identifier as value",
        "custom_tags" : "List of custom tags created on the instance",
        "time_required": "Time required to realize the case"
    })
    def post(self):
        user = utils.get_user_from_api(request.headers)

        if request.json:
            verif_dict = CaseModelApi.verif_create_case_task(request.json, True)

            if "message" not in verif_dict:
                case = CaseModel.create_case(verif_dict, user)
                return {"message": f"Case created, id: {case.id}", "case_id": case.id}, 201

            return verif_dict, 400
        return {"message": "Please give data"}, 400
    

@api.route('/<id>/edit', methods=['POST'])
@api.doc(description='Edit a case', params={'id': 'id of a case'})
class EditCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"title": "Title for a case", 
                     "description": "Description of a case", 
                     "deadline_date": "Date(%Y-%m-%d)", 
                     "deadline_time": "Time(%H-%M)",
                     "tags": "list of tags from taxonomies",
                     "clusters": "list of tags from galaxies",
                     "identifier": "Dictionnary with connector as key and identifier as value",
                     "custom_tags" : "List of custom tags created on the instance"
                    })
    def post(self, id):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(id, current_user) or current_user.is_admin():
            if request.json:
                verif_dict = CaseModelApi.verif_edit_case(request.json, id)

                if "message" not in verif_dict:
                    CaseModel.edit_case(verif_dict, id, current_user)
                    return {"message": f"Case {id} edited"}, 200

                return verif_dict, 400
            return {"message": "Please give data"}, 400
        return {"message": "Permission denied"}, 403
    
@api.route('/<cid>/fork', methods=['POST'])
@api.doc(description='Fork a case', params={'cid': 'id of a case'})
class ForkCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "case_title_fork": "Required. Title for the case"
    })
    def post(self, cid):
        user = utils.get_user_from_api(request.headers)

        if request.json:
            if "case_title_fork" in request.json:
                new_case = CaseModel.fork_case_core(cid, request.json["case_title_fork"], user)
                if type(new_case) == dict:
                    return new_case, 400
                return {"new_case_id": new_case.id}, 201
            return {"message": "Need to pass 'case_title_fork'"}, 400
        return {"message": "Please give data"}, 400

@api.route('/not_completed')
@api.doc(description='Get all not completed cases')
class GetCases_not_completed(Resource):
    method_decorators = [api_required]
    def get(self):
        cases = CommonModel.get_case_by_completed(False)
        return {"cases": [case.to_json() for case in cases]}, 200
    
@api.route('/completed')
@api.doc(description='Get all completed cases')
class GetCases_not_completed(Resource):
    method_decorators = [api_required]
    def get(self):
        cases = CommonModel.get_case_by_completed(True)
        return {"cases": [case.to_json() for case in cases]}, 200    
    
@api.route('/title', methods=["POST"])
@api.doc(description='Get a case by title')
class GetCaseTitle(Resource):
    method_decorators = [api_required]
    @api.doc(params={"title": "Title of a case"})
    def post(self):
        if "title" in request.json:
            case = CommonModel.get_case_by_title(request.json["title"])
            if case:
                case_json = case.to_json()
                orgs = CommonModel.get_orgs_in_case(case.id)
                case_json["orgs"] = [{"id": org.id, "uuid": org.uuid, "name": org.name} for org in orgs]            
                return case_json, 200
            return {"message": "Case not found"}, 404
        return {"message": "Need to pass a title"}, 404
    
@api.route('/<cid>/complete')
@api.doc(description='Complete a case', params={'cid': 'id of a case'})
class CompleteCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            case = CommonModel.get_case(cid)
            if case:
                if CaseModel.complete_case(cid, current_user):
                    return {"message": f"Case {cid} completed"}, 200
                return {"message": f"Error case {cid} completed"}, 400
            return {"message": "Case not found"}, 404
        return {"message": "Permission denied"}, 403

@api.route('/<cid>/delete')
@api.doc(description='Delete a case', params={'cid': 'id of a case'})
class DeleteCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if CaseModel.delete_case(cid, current_user):
                return {"message": "Case deleted"}, 200
            return {"message": "Error case deleted"}, 400
        return {"message": "Permission denied"}, 403
    
@api.route('/<cid>/add_org', methods=['POST'])
@api.doc(description='Add an org to the case', params={'cid': 'id of a case'})
class AddOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"name": "Name of the organisation", "oid": "id of the organisation"})
    def post(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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


@api.route('/<cid>/remove_org/<oid>', methods=['GET'])
@api.doc(description='Add an org to the case', params={'cid': 'id of a case', "oid": "id of an org"})
class RemoveOrgCase(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, oid):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            org = CommonModel.get_org(oid)

            if org:
                if CommonModel.get_org_in_case(org.id, cid):
                    if CaseModel.remove_org_case(cid, org.id, current_user):
                        return {"message": f"Org deleted from case {cid}"}, 200
                    return {"message": f"Error Org deleted from case {cid}"}, 400
                return {"message": "Org not in case"}, 404
            return {"message": "Org not found"}, 404
        return {"message": "Permission denied"}, 403
    
@api.route('/<cid>/history', methods=['GET'])
@api.doc(description='Get history of a case', params={'cid': 'id of a case'})
class History(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            history = CommonModel.get_history(case.uuid)
            if history:
                return {"history": history}
            return {"history": None}
        return {"message": "Case Not found"}, 404

@api.route('/<cid>/create_template', methods=["POST"])
@api.doc(description='Create a template form case', params={'cid': 'id of a case'})
class CreateTemplate(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"title_template": "Title for the template that will be create"})
    def post(self, cid):
        if "title_template" in request.json:
            if CommonModel.get_case(cid):
                current_user = utils.get_user_from_api(request.headers)
                new_template = CaseModel.create_template_from_case(cid, request.json["title_template"], current_user)
                if type(new_template) == dict:
                    return new_template
                return {"template_id": new_template.id}, 201
            return {"message": "Case not found"}, 404
        return {"message": "'title_template' is missing"}, 400


@api.route('/<cid>/recurring', methods=['POST'])
@api.doc(description='Set a case recurring')
class RecurringCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "once": "Date(%Y-%m-%d)", 
        "daily": "Boolean", 
        "weekly": "Date(%Y-%m-%d). Start date.", 
        "monthly": "Date(%Y-%m-%d). Start date.",
        "remove": "Boolean"
    })
    def post(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                verif_dict = CaseModelApi.verif_set_recurring(request.json)

                if "message" not in verif_dict:
                    CaseModel.change_recurring(verif_dict, cid, current_user)
                    return {"message": "Recurring changed"}, 200
                return verif_dict
            return {"message": "Please give data"}, 400
        return {"message": "Permission denied"}, 403


@api.route('/search', methods=['POST'])
@api.doc(description='Get cases matching search terms')
class SearchCase(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "search": "Required. Search terms"
    })
    def post(self):
        if "search" in request.json:
            cases = CommonModel.search(request.json["search"])
            if cases:
                return {"cases": [case.to_json() for case in cases]}, 200
            return {"message": "No case", 'toast_class': "danger-subtle"}, 404
        return {"message": "Please enter terms"}, 400
    
@api.route('/<cid>/change_status', methods=['POST'])
@api.doc(description='Change the status of the case')
class ChangeStatusCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "status_id": "Required. Status id"
    })
    def post(self, cid):
        if "status_id" in request.json:
            case = CommonModel.get_case(cid)
            if case:
                current_user = utils.get_user_from_api(request.headers)
                if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                    CaseModel.change_status_core(request.json["status_id"], case, current_user)
                    return {"message": "Status changed"}, 200
                return {"message": "Permission denied"}, 403
            return {"message": "Case doesn't exist"}, 404
        return {"message": "Please enter a status id"}, 400
    

@api.route('/check_case_title_exist', methods=['POST'])
@api.doc(description='Check if a case with the title exist', params={'title': 'title of a case'})
class CheckTitle(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        'title': 'Required. Title of a case'
    })
    def post(self):
        if "title" in request.json:
            if CommonModel.get_case_by_title(request.json["title"]):
                return {"title_already_exist": True}, 200
            return {"title_already_exist": False}, 200
        return {"message": "Please give 'title'"}, 400
    

@api.route('/get_taxonomies', methods=['GET'])
@api.doc(description='Get all taxonomies')
class GetTaxonomies(Resource):
    method_decorators = [api_required]
    def get(self):
        return {"taxonomies": CommonModel.get_taxonomies()}, 200
    
@api.route('/get_tags', methods=['POST'])
@api.doc(description='Get all tags by given taxonomies')
class GetTags(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        'taxonomies': 'Required. List of taxonomies'
    })
    def post(self):
        if "taxonomies" in request.json:
            taxos = request.json["taxonomies"]
            return {"tags": CommonModel.get_tags(taxos)}, 200
        return {"message": "Please give 'taxonomies'"}, 400
    
@api.route('/get_taxonomies_case/<cid>', methods=['GET'])
@api.doc(description='Get all tags and taxonomies in a case')
class GetTaxonomiesCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            tags = CommonModel.get_case_tags(case.id)
            taxonomies = []
            if tags:
                taxonomies = [tag.split(":")[0] for tag in tags]
            return {"tags": tags, "taxonomies": taxonomies}, 200
        return {"message": "Case Not found"}, 404

@api.route('/get_galaxies', methods=['GET'])
@api.doc(description='Get all galaxies')
class GetGalaxies(Resource):
    method_decorators = [api_required]
    def get(self):
        return {"galaxies": CommonModel.get_galaxies()}, 200

@api.route('/get_galaxies_case/<cid>', methods=['GET'])
@api.doc(description='Get all tags and galaxies in a case', params={'galaxies': 'List of galaxies'})
class GetGalaxiesCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
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
            return {"clusters": clusters, "galaxies": galaxies}, 200
        return {"message": "Case Not found"}, 404
    


@api.route('/get_modules', methods=['GET'])
@api.doc(description='Get all modules')
class GetModules(Resource):
    method_decorators = [api_required]
    def get(self):
        return {"modules": CaseModel.get_modules()}, 200

@api.route('/<cid>/get_instance_module', methods=['GET'])
@api.doc(description='Get all instances for a module', params={'module': 'Name of the module to use', "type": "type of the module"})
class GetInstanceModules(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if "module" in request.args:
                module = request.args.get("module")
            if "type" in request.args:
                type_module = request.args.get("type")
            else:
                return{"message": "Module type error"}, 400
            return {"instances": CaseModel.get_instance_module_core(module, type_module, case.id, current_user.id)}, 200
        return {"message": "Case Not found"}, 404
    

@api.route('/<cid>/call_module_case', methods=['POST'])
@api.doc(description='Call a module on a case')
class CallModuleCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "module": "Required. Name of the module to call",
        "instance_id": "Required. List of name or id of instances to use for the module"
    })
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
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
    

@api.route('/<cid>/get_note')
@api.doc(description='Get note of a case', params={'cid': 'id of a case'})
class GetNote(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            return {"note": case.notes}
        return {"message": "Case not found"}, 404


@api.route('/<cid>/get_all_users', methods=['GET'])
@api.doc(description='Get list of user that can be assign', params={'cid': 'id of a case'})
class GetAllUsers(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        case = CommonModel.get_case(cid)
        if case:
            users_list = list()
            for org in CommonModel.get_all_org_case(case):
                for user in org.users:
                    if not user == current_user:
                        users_list.append(user.to_json())
            return {"users": users_list}, 200
        return {"message": "Case not found"}, 404

@api.route('/list_status', methods=['GET'])
@api.doc(description='List all status')
class ListStatus(Resource):
    method_decorators = [api_required]
    def get(self):
        return [status.to_json() for status in CommonModel.get_all_status()], 200
    

##############
# Connectors #
##############

@api.route('/get_connectors', methods=['GET'])
@api.doc(description='Get all connectors and instances')
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
    
@api.route('/get_case_connectors/<cid>', methods=['GET'])
@api.doc(description='Get all connectors instance for a case')
class GetConnectorsCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            instance_list = []
            for case_instance in CommonModel.get_case_connectors(case.id):
                loc_instance = CommonModel.get_instance(case_instance.instance_id)
                instance_list.append({
                    "id": loc_instance.id,
                    "name": loc_instance.name,
                    "identifier": case_instance.identifier
                })
            return {"connectors": instance_list}, 200
        return {"message": "Case Not found"}, 404
    
@api.route('/<cid>/add_connectors', methods=['POST'])
@api.doc(description='Add connectors to a case')
class AddConnectorsCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "connectors": "Required. List of connectors instance. Dict with 'name' and 'identifier' as keys."
    })
    def post(self, cid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "connectors" in request.json:
                    if CaseModel.add_connector(cid, request.json):
                        return {"message": "Connector added"}, 200
                    return {"message": "Error Connector added"}, 400
                return {"message": "Please give a list of connectors"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    
@api.route('/<cid>/edit_connector/<ciid>', methods=['POST'])
@api.doc(description='Edit connector')
class EditConnectorsCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "identifier": "Required. Identifier used by modules to identify where to send data."
    })
    def post(self, cid, ciid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "identifier" in request.json:
                    if CaseModel.edit_connector(cid, ciid, request.json):
                        return {"message": "Connector edited"}, 200
                    return {"message": "Error Connector edited"}, 400
                return {"message": "Please give a list of connectors"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404
    
@api.route('/<cid>/remove_connector/<ciid>', methods=['GET'])
@api.doc(description='Remove a connector')
class RemoveConnectors(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, ciid):
        if CommonModel.get_case(cid):
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if CaseModel.remove_connector(cid, ciid):
                    return {"message": "Connector removed"}, 200
                return {"message": "Error Connector removed"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case doesn't exist"}, 404

#########
# Tasks #
#########

@api.route('/<cid>/tasks')
@api.doc(description='Get all tasks for a case', params={'cid': 'id of a case'})
class GetTasks(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            tasks = list()
            for task in case.tasks:
                if not task.completed:
                    tasks.append(task.to_json())

            return tasks, 200
        return {"message": "Case not found"}, 404
    

@api.route('/<cid>/tasks_finished')
@api.doc(description='Get all tasks for a case', params={'cid': 'id of a case'})
class GetTasksFinished(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            tasks = list()
            for task in case.tasks:
                if task.completed:
                    tasks.append(task.to_json())

            return tasks, 200
        return {"message": "Case not found"}, 404
    

@api.route('/<cid>/create_task', methods=['POST'])
@api.doc(description='Create a new task to a case', params={'cid': 'id of a case'})
class CreateTask(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={
        "title": "Required. Title for a task", 
        "description": "Description of a task",
        "url": "Link to a tool or a ressource",
        "deadline_date": "Date(%Y-%m-%d)", 
        "deadline_time": "Time(%H-%M)",
        "tags": "list of tags from taxonomies",
        "clusters": "list of tags from galaxies",
        "identifier": "Dictionnary with connector as key and identifier as value",
        "custom_tags" : "List of custom tags created on the instance",
        "time_required": "Time required to realize the task"
    })
    def post(self, cid):
        current_user = utils.get_user_from_api(request.headers)
        if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
            if request.json:
                verif_dict = CaseModelApi.verif_create_case_task(request.json, False)

                if "message" not in verif_dict:
                    task = TaskModel.create_task(verif_dict, cid, current_user)
                    return {"message": f"Task {task.id} created for case id: {cid}", "task_id": task.id}, 201
                return verif_dict, 400
            return {"message": "Please give data"}, 400
        return {"message": "Permission denied"}, 403
    

@api.route('/<cid>/move_task_up/<tid>', methods=['GET'])
@api.doc(description='Move the task up', params={"cid": "id of a case", "tid": "id of a task"})
class MoveTaskUp(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, tid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                task = CommonModel.get_task(tid)
                if task:
                    TaskModel.change_order(case, task, "true")
                    return {"message": "Order changed"}, 200
                return {"message": "Task Not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Case Not found"}, 404

@api.route('/<cid>/move_task_down/<tid>', methods=['GET'])
@api.doc(description='Move the task down', params={"cid": "id of a case", "tid": "id of a task"})
class MoveTaskDown(Resource):
    method_decorators = [editor_required, api_required]
    def get(self, cid, tid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                task = CommonModel.get_task(tid)
                if task:
                    TaskModel.change_order(case, task, "false")
                    return {"message": "Order changed"}, 200
                return {"message": "Task Not found"}, 404
            return {"message": "Permission denied"}, 403
        return {"message": "Case Not found"}, 404


@api.route('/<cid>/all_notes')
@api.doc(description='Get all notes of a case', params={'cid': 'id of a case'})
class GetAllNotes(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            return {"notes": CaseModel.get_all_notes(case)}
        return {"message": "Case not found"}, 404


@api.route('/<cid>/modif_case_note', methods=['POST'])
@api.doc(description='Edit note of a case', params={'cid': 'id of a case'})
class ModifNoteCase(Resource):
    method_decorators = [editor_required, api_required]
    @api.doc(params={"note": "note to create or modify"})
    def post(self, cid):
        case = CommonModel.get_case(cid)
        if case:
            current_user = utils.get_user_from_api(request.headers)
            if CaseModel.get_present_in_case(cid, current_user) or current_user.is_admin():
                if "note" in request.json:
                    if CaseModel.modif_note_core(cid, current_user, request.json["note"]):
                        return {"message": f"Note for Case {cid} edited"}, 200
                    return {"message": f"Error Note for Case {cid} edited"}, 400
                return {"message": "Key 'note' not found"}, 400
            return {"message": "Permission denied"}, 403
        return {"message": "Case not found"}, 404
    
