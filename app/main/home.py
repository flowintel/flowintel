from flask import Flask, Blueprint, render_template

home_blueprint = Blueprint(
    'home',
    __name__,
    template_folder='templates',
    static_folder='static'
)


@home_blueprint.route("/")
def home():
    return render_template("home.html")