from flask import Blueprint, request
from . import tools_core as ToolModel
from . import tools_core_api as ApiToolModel
from . import common_template_core as CommonModel
from . import task_template_core as TaskModel

from flask_restx import Api, Resource
from ..decorators import api_required


api_templating_blueprint = Blueprint('api_templating', __name__)
api = Api(api_templating_blueprint,
        title='Flowintel-cm API', 
        description='API to manage a case management instance.', 
        version='0.1', 
        default='GenericAPI', 
        default_label='Generic Flowintel-cm API', 
        doc='/doc'
    )



@api.route('/cases')
@api.doc(description='Get all case template')
class GetCaseTemplates(Resource):
    method_decorators = [api_required]
    def get(self):
        templates = CommonModel.get_all_case_templates()
        return {"templates": [template.to_json() for template in templates]}, 200
    
@api.route('/case/<cid>')
@api.doc(description='Get a case template', params={'cid': 'id of a case template'})
class GetCaseTemplate(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case_template = CommonModel.get_case_template(cid)
        if case_template:
            loc_case = case_template.to_json()
            tasks_template = CommonModel.get_task_by_case(cid)
            loc_case["tasks"] = [task_template.to_json() for task_template in tasks_template]
            return loc_case, 200
        return {"message": "Case template not found"}, 404
    

@api.route('/case/title', methods=["POST"])
@api.doc(description='Get a case by title')
class GetCaseTitle(Resource):
    method_decorators = [api_required]
    @api.doc(params={"title": "Title of a case"})
    def post(self):
        if "title" in request.json:
            case = CommonModel.get_case_by_title(request.json["title"])
            if case:
                case_json = case.to_json()          
                return case_json, 200
            return {"message": "Case not found"}, 404
        return {"message": "Need to pass a title"}, 404


@api.route('/create_case')
@api.doc(description='Create a new case template')
class CreateCaseTemaplte(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "title": "Required. Title for the template",
        "description": "Description of the template"
        })
    def post(self):
        if request.json:
            verif_dict = ApiToolModel.verif_create_case_template(request.json)
            if "message" not in verif_dict:
                template = ToolModel.create_case_template(verif_dict)
                return {"message": f"Template created, id: {template.id}"}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    
@api.route('/edit_case/<cid>')
@api.doc(description='Edit a case template', params={'cid': 'id of a case template'})
class EditCaseTemaplte(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "title": "Title for the template",
        "description": "Description of the template"
        })
    def post(self, cid):
        if request.json:
            verif_dict = ApiToolModel.verif_edit_case_template(request.json, cid)
            if "message" not in verif_dict:
                ToolModel.edit_case_template(verif_dict, cid)
                return {"message": f"Template case edited"}, 200
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    

@api.route('/case/<cid>/add_tasks')
@api.doc(description='Add a task template to a case template', params={'cid': 'id of a case template'})
class AddTaskCase(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "tasks": "List of id of tasks template"
        })
    def post(self, cid):
        template = CommonModel.get_case_template(cid)
        if template:
            if request.json:
                if 'tasks' in request.json:
                    form_dict = request.json
                    ToolModel.add_task_case_template(form_dict, cid)
                    return {"message": "Tasks added"}, 200
                return {"message": "The list 'tasks' is missing"}, 400
            return {"message": "Please give data"}, 400
        return {"message": "Case template not found"}, 404
    

@api.route('/case/<cid>/remove_task/<tid>')
@api.doc(description='Delete a case template', params={'cid': 'id of a case template', 'tid': 'id of the task template'})
class RemoveTaskCaseTemplate(Resource):
    method_decorators = [api_required]
    def get(self, cid, tid):
        if CommonModel.get_case_template(cid):
            if CommonModel.get_task_template(tid):
                if ToolModel.remove_task_case(cid, tid):
                    return {"message": "Task template removed"}, 200
                return {"message": "Error task template removed"}, 400
            return {"message": "Task template not found"}, 404
        return {"message": "Case template not found"}, 404
    

@api.route('/delete_case/<cid>')
@api.doc(description='Delete a case template', params={'cid': 'id of a case template'})
class DeleteCaseTemplate(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        if CommonModel.get_case_template(cid):
            if ToolModel.delete_case_template(cid):
                return {"message": "Case template deleted"}, 200
            return {"message": "Error case template deleted"}, 400
        return {"message": "Template not found"}, 404
    

@api.route('/create_case_from_template/<cid>')
@api.doc(description='Create a case from a case template', params={'cid': 'id of a case template'})
class CreateCaseFromTemplate(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "title": "Title of the case to create"
        })
    def post(self, cid):
        template = CommonModel.get_case_template(cid)
        if template:
            if request.json:
                if "title" in request.json:
                    new_case = ToolModel.create_case_from_template(cid, request.json["title"], ApiToolModel.get_user_api(request.headers["X-API-KEY"]))
                    if type(new_case) == dict:
                        return new_case
                    return {"message": f"New case created, id: {new_case.id}"}, 201
                return {"message": "The field 'title' is missing"}, 400
            return {"message": "Please give data"}, 400
        return {"message": "Case template not found"}, 404
    

@api.route('/get_taxonomies_case/<cid>', methods=["GET"])
@api.doc(description='Get Taxonomies of a case', params={'cid': 'id of a case template'})
class GetTaxonomiesCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case_template(cid)
        if case:
            tags = CommonModel.get_case_template_tags(case.id)
            taxonomies = []
            if tags:
                taxonomies = [tag.split(":")[0] for tag in tags]
            return {"tags": tags, "taxonomies": taxonomies}
        return {"message": "Case Not found"}, 404
    

@api.route('/get_galaxies_case/<cid>', methods=["GET"])
@api.doc(description='Get Galaxies of a case', params={'cid': 'id of a case template'})
class GetGalaxiesCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
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
        return {"message": "Case Not found"}, 404
    
@api.route('/get_connectors_case/<cid>', methods=["GET"])
@api.doc(description='Get Connectors of a case', params={'cid': 'id of a case template'})
class GetConnectorsCase(Resource):
    method_decorators = [api_required]
    def get(self, cid):
        case = CommonModel.get_case_template(cid)
        if case:
            return {"connectors": [CommonModel.get_instance(case_instance.instance_id).name for case_instance in CommonModel.get_case_connectors(case.id) ]}
        return {"message": "Case Not found"}, 404

##########
## Task ##
##########


@api.route('/tasks')
@api.doc(description='Get all task template')
class GetTaskTemplates(Resource):
    method_decorators = [api_required]
    def get(self):
        templates = CommonModel.get_all_task_templates()
        return {"templates": [template.to_json() for template in templates]}, 200
    
@api.route('/task/<tid>')
@api.doc(description='Get a task template', params={'tid': 'id of a task template'})
class GetTaskTemplate(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        template = CommonModel.get_task_template(tid)
        if template:
            return template.to_json(), 200
        return {"message": "Task template not found"}, 404

@api.route('/create_task')
@api.doc(description='Create new task template')
class CreateTaskTemaplte(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "title": "Required. Title for the template",
        "description": "Description of the template",
        "url": "Link to a tool or a ressource"
        })
    def post(self):
        if request.json:
            verif_dict = ApiToolModel.verif_add_task_template(request.json)
            if "message" not in verif_dict:
                template = TaskModel.add_task_template_core(verif_dict)
                return {"message": f"Template created, id: {template.id}"}, 201
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    

@api.route('/edit_task/<tid>')
@api.doc(description='Edit new case template', params={'tid': 'id of a task template'})
class EditCaseTemaplte(Resource):
    method_decorators = [api_required]
    @api.doc(params={
        "title": "Title for the template",
        "description": "Description of the template",
        "url": "Link to a tool or a ressource"
        })
    def post(self, tid):
        if request.json:
            verif_dict = ApiToolModel.verif_edit_task_template(request.json, tid)
            if "message" not in verif_dict:
                TaskModel.edit_task_template(verif_dict, tid)
                return {"message": f"Template edited"}, 200
            return verif_dict, 400
        return {"message": "Please give data"}, 400
    

@api.route('/delete_task/<tid>')
@api.doc(description='Delete a task template')
class DeleteTaskTemplate(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        if CommonModel.get_task_template(tid):
            if TaskModel.delete_task_template(tid):
                return {"message": "Task template deleted"}, 200
            return {"message": "Error task template deleted"}, 400
        return {"message": "Template not found"}, 404
    

@api.route('/get_taxonomies_task/<tid>', methods=["GET"])
@api.doc(description='Get Taxonomies of a task', params={'tid': 'id of a task template'})
class GetTaxonomiesTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task_template(tid)
        if task:
            tags = CommonModel.get_task_template_tags(task.id)
            taxonomies = []
            if tags:
                taxonomies = [tag.split(":")[0] for tag in tags]
            return {"tags": tags, "taxonomies": taxonomies}
        return {"message": "Task Not found"}, 404
    
@api.route('/get_galaxies_task/<tid>', methods=["GET"])
@api.doc(description='Get Galaxies of a task', params={'tid': 'id of a task template'})
class GetGalaxiesTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
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
        return {"message": "Case Not found"}, 404
    
@api.route('/get_connectors_task/<tid>', methods=["GET"])
@api.doc(description='Get Connectors of a task', params={'tid': 'id of a task template'})
class GetConnectorsTask(Resource):
    method_decorators = [api_required]
    def get(self, tid):
        task = CommonModel.get_task_template(tid)
        if task:
            return {"connectors": [CommonModel.get_instance(task_instance.instance_id).name for task_instance in CommonModel.get_task_connectors(task.id) ]}
        return {"message": "Task Not found"}, 404
