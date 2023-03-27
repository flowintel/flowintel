from functools import wraps

from flask import abort
from flask_login import current_user


def permission_required(perm):
    """Restrict a view to users with the given permission."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if perm == "admin":
                if not current_user.is_admin():
                    abort(403)
            if perm == "read_only":
                if current_user.read_only():
                    abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    return permission_required("admin")(f)

def editor_required(f):
    return permission_required("read_only")(f)