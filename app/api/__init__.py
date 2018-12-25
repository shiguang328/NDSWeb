from flask import Blueprint

api = Blueprint('api', __name__)
auth = Blueprint('auth', 'auth')

from . import authentication, user, user_admin, cars, drivers, tasks, ghost_car