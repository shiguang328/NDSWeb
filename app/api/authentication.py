from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from ..models import User
from . import api
from .errors import unauthorized, forbidden

http_auth = HTTPBasicAuth()


@http_auth.verify_password
def verify_password(email_or_token, password):
    if email_or_token == '':
        return False
    if password is None or password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.objects(email=email_or_token).first()  # pylint: disable=no-member
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


@http_auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


# 若api蓝本中所有的路由都需要相同的方式保护，可以使用before_request装饰器，
# 此处将login_required应用到蓝本内所有请求
# @api.before_request
@http_auth.login_required
def before_request():
    if g.current_user.is_authenticated:
        g.current_user.ping()


# @api.route('/tokens/', methods=['POST'])
def get_token():
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})
        