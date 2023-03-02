from .. import db
from ..db_class.db import User
from flask import Blueprint, render_template, redirect, url_for, request, flash
from .form import RegistrationForm, LoginForm
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from .account_core import *
from ..utils.create_user import create_user

account_blueprint = Blueprint(
    'account',
    __name__,
    template_folder='templates',
    static_folder='static'
)



@account_blueprint.route("/")
@login_required
def index():
    users = db.session.execute(db.select(User)).scalars()

    return render_template("account/account_index.html", users=users)


@account_blueprint.route("/add_user", methods=['GET','POST'])
@login_required
def add_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        add_user_core(form)
        return redirect("/account")
    return render_template("account/add_user.html", form=form)


@account_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """Log in an existing user."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.password_hash is not None and \
                user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash('You are now logged in. Welcome back!', 'success')
            return redirect(request.args.get('next') or "home.home")
        else:
            flash('Invalid email or password.', 'error')
    return render_template('account/login.html', form=form)

@account_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home.home'))

# TO BE REMOVED
@account_blueprint.route('/create')
def create():
    create_user()
    return redirect(url_for('home.home'))