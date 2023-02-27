from .. import db
from ..db_class.db import User
from flask import Blueprint, render_template, redirect, url_for
from .form import RegistrationForm

account_blueprint = Blueprint(
    'account',
    __name__,
    template_folder='templates',
    static_folder='static'
)




@account_blueprint.route("/")
def account():

    users = db.session.execute(db.select(User)).scalars()

    return render_template("account/account.html", users=users)


@account_blueprint.route("/add_user", methods=['GET','POST'])
def add_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect("/account")
    return render_template("account/add_user.html", form=form)
