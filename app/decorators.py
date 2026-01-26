from functools import wraps

from flask import abort, request
from flask_login import current_user
from .utils.utils import get_user_api, verif_api_key


def permission_required(perm):
    """Restrict a view to users with the given permission."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if perm == "admin":
                if request.path.startswith("/api/"):
                    user = get_user_api(request.headers["X-API-KEY"])
                    if not user.is_admin():
                        abort(403)
                elif not current_user.is_admin():
                    abort(403)
            elif perm == "admin_or_org_admin":
                if request.path.startswith("/api/"):
                    user = get_user_api(request.headers["X-API-KEY"])
                    if not (user.is_admin() or user.is_org_admin()):
                        abort(403)
                elif not (current_user.is_admin() or current_user.is_org_admin()):
                    abort(403)
            elif perm == "read_only":
                if request.path.startswith("/api/"):
                    user = get_user_api(request.headers["X-API-KEY"])
                    if user.read_only():
                        abort(403)
                elif current_user.read_only():
                    abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def verification_required():
    """Restrict an api access to users without a key"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.path.startswith("/api/") and verif_api_key(request.headers):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    return permission_required("admin")(f)

def admin_or_org_admin_required(f):
    return permission_required("admin_or_org_admin")(f)

def editor_required(f):
    return permission_required("read_only")(f)

def api_required(f):
    return verification_required()(f)