import os
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import desc

from ..db_class.db import Case

from ..case import common_core as CommonModel

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
    # display 10 without private that cannot be seen
    cp = 0
    last_case = []
    all_case = Case.query.order_by(desc('last_modif')).all()
    for case in all_case:
        if cp < 10:
            if case.is_private:
                if CommonModel.get_present_in_case(case.id, current_user) or current_user.is_admin():
                    last_case.append(case.to_json())
                    cp += 1
            else:
                last_case.append(case.to_json())
                cp += 1
    return {"cases": last_case}, 200


@home_blueprint.route("/version")
@login_required
def version():
    with open(os.path.join(os.getcwd(),"version")) as read_version:
        loc = read_version.readlines()
    return {"version": loc[0]}