from flask import Flask, Blueprint, render_template
from flask_login import login_required

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