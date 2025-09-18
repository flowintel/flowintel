import os
from flask import Blueprint
from flask_restx import Api

api_blueprint = Blueprint(
    "api", __name__, url_prefix="/api"
)

authorizations = {
    "apikey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-KEY",
    }
}

def version():
    with open(os.path.join(os.getcwd(),"version")) as read_version:
        loc = read_version.readlines()
    return loc[0].rstrip()


api = Api(api_blueprint,
    title='flowintel API', 
    description='API to manage a case management instance.', 
    version=version(), 
    default='GenericAPI', 
    default_label='Generic flowintel API', 
    doc='/',
    security="apikey",
    authorizations=authorizations
)

from .case.case_api import case_ns
from .case.task_api import task_ns
from .admin.admin_api import admin_ns
from .analyzer.analyzer_api import analyzer_ns
from .connectors.connectors_api import connectors_ns
from .custom_tags.custom_tags_api import custom_tags_ns
from .my_assignment.my_assignment_api import my_assignment_ns
from .templating.templating_api import templating_ns
from .tools.tools_api import importer_ns, case_misp_ns

api.add_namespace(case_ns, path="/case")
api.add_namespace(task_ns, path="/task")
api.add_namespace(admin_ns, path="/admin")
api.add_namespace(analyzer_ns, path="/analyzer")
api.add_namespace(connectors_ns, path="/connectors")
api.add_namespace(custom_tags_ns, path="/custom_tags")
api.add_namespace(my_assignment_ns, path="/my_assignment")
api.add_namespace(templating_ns, path="/templating")
api.add_namespace(importer_ns, path="/importer")
api.add_namespace(case_misp_ns, path="/case_from_misp")




