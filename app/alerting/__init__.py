from flask import Blueprint

alerting_blueprint = Blueprint("alerting", __name__, template_folder="templates")

from . import alerting
