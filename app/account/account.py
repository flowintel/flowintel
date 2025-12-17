from ..db_class.db import User, Role
from .form import LoginForm, EditUserFrom
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session, abort
from .form import LoginForm, EditUserFrom, RequestPasswordResetForm
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from . import account_core as AccountModel
from ..utils.utils import form_to_dict
from ..utils.logger import flowintel_log
from ..notification import notification_core as NotifModel
import logging
import time
import secrets

from wtforms.validators import Email, ValidationError

logger = logging.getLogger()

# Rate limiting
RATE_LIMIT_WINDOW = 300  # 5 minutes
TOKEN_EXPIRY_TIME = 300  # 5 minutes
MAX_RESET_REQUESTS = 3   # Max requests per IP per window
MAX_LOGIN_ATTEMPTS = 5   # Max login per IP per window
URL_SAFE_TOKENS = 32     # Length of URL safe tokens

account_blueprint = Blueprint(
    'account',
    __name__,
    template_folder='templates',
    static_folder='static'
)


def get_client_ip():
    """Get client IP"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr


def check_rate_limit(key_prefix, max_attempts, window):
    """Check if the request exceeds rate limit"""
    client_ip = get_client_ip()
    session_key = f"{key_prefix}{client_ip}"
    current_time = time.time()
    
    if session_key not in session:
        session[session_key] = {'attempts': 0, 'first_attempt': current_time}
    
    attempt_data = session[session_key]
    time_passed = current_time - attempt_data['first_attempt']
    
    if time_passed > window:
        session[session_key] = {'attempts': 1, 'first_attempt': current_time}
        return True, 0
    
    if attempt_data['attempts'] >= max_attempts:
        remaining_time = int(window - time_passed)
        return False, remaining_time
    
    session[session_key]['attempts'] += 1
    return True, 0


def create_password_reset_token():
    return secrets.token_urlsafe(URL_SAFE_TOKENS)


def validate_password_reset_token():
    token = session.get('password_reset_token')
    token_time = session.get('password_reset_token_time')
    
    if not token or not token_time:
        return False
    
    if time.time() - token_time > TOKEN_EXPIRY_TIME:
        session.pop('password_reset_token', None)
        session.pop('password_reset_token_time', None)
        return False
    
    return True



@account_blueprint.route("/")
@login_required
def index():
    return render_template("account/account_index.html", user=current_user)


@account_blueprint.route("/edit", methods=['GET', 'POST'])
@login_required
def edit_user():
    """Edit the user"""
    form = EditUserFrom()

    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        # Only include password if change_password is checked
        if not form.change_password.data:
            form_dict.pop('password', None)
            form_dict.pop('password2', None)
        AccountModel.edit_user_core(form_dict, current_user.id)
        return redirect("/account")
    else:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.nickname.data = current_user.nickname
        form.email.data = current_user.email
        form.matrix_id.data = current_user.matrix_id

    return render_template("account/edit_user.html", form=form)


@account_blueprint.route("/change_api_key", methods=['GET', 'POST'])
@login_required
def change_api_key():
    """Change the api key of the user"""
    api_key = AccountModel.change_api_key(current_user)
    if api_key:
        return {"message": "API key changed", "toast_class": "success-subtle", "api_key": api_key}, 200
    return {"message": "Something went wrong", "toast_class": "warning-subtle"}, 400


@account_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """Log in an existing user."""
    form = LoginForm()
    show_reset_link = False
    
    if form.validate_on_submit():
        # Check rate limit for login attempts
        is_allowed, remaining_time = check_rate_limit('login_attempts_', MAX_LOGIN_ATTEMPTS, RATE_LIMIT_WINDOW)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for login from IP: {get_client_ip()}")
            flash(f'Too many login attempts. Please try again in {remaining_time} seconds.', 'error')
            return render_template('account/login.html', form=form, show_reset_link=False)
        
        try:
            Email(form.email.data)
        except ValidationError:
            flash('Invalid email or password.', 'error')
            flowintel_log("audit", 401, "Failed login attempt - Invalid email format", Email=form.email.data)
            token = create_password_reset_token()
            session['password_reset_token'] = token
            session['password_reset_token_time'] = time.time()
            session['failed_login_email'] = form.email.data  # Store for pre-filling
            show_reset_link = True
        else:
            user = User.query.filter_by(email=form.email.data).first()
            if user is not None and user.password_hash is not None and \
                    user.verify_password(form.password.data):
                login_user(user, form.remember_me.data)
                flowintel_log("audit", 200, "Successful login", Email=form.email.data)
                # Clear rate limit on successful login
                client_ip = get_client_ip()
                session.pop(f'login_attempts_{client_ip}', None)
                session.pop('password_reset_token', None)
                session.pop('password_reset_token_time', None)
                session.pop('failed_login_email', None)
                flash('You are now logged in. Welcome back!', 'success')
                return redirect(request.args.get('next') or "/")
            else:
                flash('Invalid email or password.', 'error')
                flowintel_log("audit", 401, "Failed login attempt - Invalid credentials", Email=form.email.data)
    return render_template('account/login.html', form=form)
                # Generate token for password reset access
                token = create_password_reset_token()
                session['password_reset_token'] = token
                session['password_reset_token_time'] = time.time()
                session['failed_login_email'] = form.email.data  # Store for pre-filling
                show_reset_link = True
                
                logger.warning(f"Failed login attempt for email: {form.email.data} from IP: {get_client_ip()}")
    
    return render_template('account/login.html', form=form, show_reset_link=show_reset_link)


@account_blueprint.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    """Request password reset from an administrator"""
    # Security check: Validate token from failed login
    if not validate_password_reset_token():
        logger.warning(f"Unauthorized access to password reset page from IP: {get_client_ip()}")
        flash('Access denied. Please attempt to login first.', 'error')
        return redirect(url_for('account.login'))
    
    form = RequestPasswordResetForm()
    if request.method == 'GET' and 'failed_login_email' in session:
        form.email.data = session.get('failed_login_email')
    
    if form.validate_on_submit():
        # Check rate limit for password reset requests
        is_allowed, remaining_time = check_rate_limit('reset_attempts_', MAX_RESET_REQUESTS, RATE_LIMIT_WINDOW)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for password reset from IP: {get_client_ip()}")
            flash(f'Too many password reset requests. Please try again in {remaining_time} seconds.', 'error')
            return render_template('account/request_password_reset.html', form=form)
        
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        
        if user:
            logger.info(f"Password reset requested for user: {email} (ID: {user.id}) from IP: {get_client_ip()}")
            
            NotifModel.create_notification_for_admins(
                message=f"Password reset requested for user {email}",
                html_icon="fa-solid fa-key",
                user_id_for_redirect=user.id
            )
        else:
            logger.warning(f"Password reset requested for non-existent user: {email} from IP: {get_client_ip()}")
        
        # Clear the token after use
        session.pop('password_reset_token', None)
        session.pop('password_reset_token_time', None)
        session.pop('failed_login_email', None)
        
        flash('If an account exists for this email, an administrator will review your request.', 'info')
        return redirect(url_for('account.login'))
    
    return render_template('account/request_password_reset.html', form=form)

@account_blueprint.route('/logout')
@login_required
def logout():
    user_email = current_user.email
    flowintel_log("audit", 200, "User logout", Email=user_email)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('account.login'))

