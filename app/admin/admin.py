from ..db_class.db import User
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from .form import RegistrationForm
from . import admin_core as AdminModel
from ..decorators import admin_required

admin_blueprint = Blueprint(
    'admin',
    __name__,
    template_folder='templates',
    static_folder='static'
)



@admin_blueprint.route("/")
@login_required
@admin_required
def index():
    users = User.query.all()

    return render_template("admin/admin_index.html", users=users)

@admin_blueprint.route("/add_user", methods=['GET','POST'])
@login_required
@admin_required
def add_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        AdminModel.add_user_core(form)
        return redirect("/")
    return render_template("admin/add_user.html", form=form)