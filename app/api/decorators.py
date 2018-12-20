from functools import wraps
from flask import g
from .errors import forbidden


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # if not g.current_user.admin:
        #     return forbidden('Insufficient permissions')
        return f(*args, **kwargs)
    return decorated_function
