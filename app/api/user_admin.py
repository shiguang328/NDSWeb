from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .authentication import http_auth
from ..models import User
from ..email import send_email
from .decorators import admin_required
from .errors import bad_request
from .validators import validate_email, validate_username, validate_length, validate_require
from flask_mongoengine import ValidationError


@api.route('/users/')
# @auth.login_required
@admin_required
def get_users():
    page = request.args.get('page', 1, type=int)
    pagination = User.objects.paginate(page=page, per_page=10)
    users = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_users', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_users', page=page+1)
    return jsonify({
        'users': [user.to_json() for user in users],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/users/<id>')
# @auth.login_required
@admin_required
def get_user(id):
    try:
        user = User.objects(id=id).first()
    except:
        abort(404)
    
    if user:
        return jsonify(user.to_json())
    else:
        abort(404)


@api.route('/users/', methods=['POST'])
# @auth.login_required
@admin_required
def new_user():
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
    user.save()
    # send a email to confirm the account
    token = user.generate_confirmation_token()
    send_email(user.email, 'Confirm Your Account',
               'auth/email/confirm', user=user, token=token)
    return jsonify(user.to_json()), 201, \
        {'Location': url_for('api.get_user', id=user.id)}


@api.route('/users/<id>', methods=['PUT'])
# @auth.login_required
@admin_required
def edit_user(id):
    user = User.objects(id=id).first()
    if user is None:
        abort(404)
    new_email = request.json.get('email')
    new_username = request.json.get('username')

    # 若更改了邮箱，检查新邮箱是否已经注册，并将确认字段'confirmed'重置
    if user.email != new_email:
        if User.objects(email=new_email).first():
            return bad_request('The input email already registered.')
        self.confirmed = False
    # 若更改了用户名，检查用户名是否重复
    if user.username != new_username:
        if User.objects(username=new_username).first():
            return bad_request('The input username already registered.')

    user.email = new_email
    user.username = new_username
    user.name = request.json.get('name')
    user.phone = request.json.get('phone')
    user.admin = request.json.get('admin')
    user.save()

    # 若用户邮箱没有确认（邮箱变更），则重新发送确认邮件。
    if not user.confirmed:
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)

    return jsonify(user.to_json())
