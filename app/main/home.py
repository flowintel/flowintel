from flask import Flask, Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import desc

from ..db_class.db import Case, Task, Task_User, Case_Org, Status

home_blueprint = Blueprint(
    'home',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@home_blueprint.route("/")
@login_required
def home():    
    return render_template("home.html")

@home_blueprint.route("/last_case")
@login_required
def last_case():
    last_case = Case.query.order_by(desc('last_modif')).limit(10).all()
    return {"cases": [c.to_json() for c in last_case]}