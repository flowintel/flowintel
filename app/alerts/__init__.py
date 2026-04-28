from flask import Blueprint

alerts_blueprint = Blueprint('alerts', __name__, template_folder='templates')

from . import alerts