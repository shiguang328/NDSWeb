from flask import request, url_for, jsonify, g, current_app
# from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from . import auth
from .authentication import http_auth
from .errors import bad_request
from .. import db
from ..models import User
from ..email import send_email
from .validators import validate_email, validate_username, validate_length, validate_require


@auth.route('/register/', methods=['POST'])
def register():
    ''' 注册接口。仅管理员及未登录的用户可以调用，已登录的普通用户禁止调用。'''
    email = request.json.get('email')
    username = request.json.get('username')
    password = request.json.get('password')

    if email is None:
        return bad_request('New user must have an email address.')
    if username is None:
        return bad_request('New user must have an username.')
    if password is None:
        return bad_request('New user must have a password.')
 
    validate_require(request.json, fields=['email', 'username', 'password', 'name'])
    validate_email(email)
    validate_username(username)
    validate_length(username, 3, 32, fieldName='Username')
    validate_length(password, 6, 32, fieldName='Password')

    if User.objects(email=request.json.get('email')).first():
        return bad_request('Email already registered.')
    if User.objects(username=request.json.get('username')).first():
        return bad_request('Username already registered.')

    user = User.from_json(request.json)
    try:
        user.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    # send a email to confirm the account
    token = user.generate_confirmation_token()
    send_email(user.email, 'Confirm Your Account',
               'auth/email/confirm', user=user, token=token)
    return jsonify(user.to_json()), 201, \
        {'Location': url_for('api.get_user', id=user.id)}