from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .authentication import http_auth
from ..models import User, Task
from ..email import send_email
from .decorators import admin_required
from .errors import bad_request, resource_not_found
from .validators import validate_email, validate_username, validate_length, validate_require
from flask_mongoengine import ValidationError


@api.route('/users/')
# @http_auth.login_required
# @admin_required
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
# @http_auth.login_required
# @admin_required
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
def new_user():
    ''' 新增用户接口。仅未登录的用户可以调用，已登录的用户禁止调用。'''
    if g.get('current_user', default=None):
        return bad_request('User %s already logged in, please logout and register again.' % g.current_user.username)

    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')

    email = request.json.get('email')
    username = request.json.get('username')
    password = request.json.get('password')

    if email is None:
        return bad_request('New user must have an email address.')
    if username is None:
        return bad_request('New user must have an username.')
    if password is None:
        return bad_request('New user must have a password.')
 
    validate_require(request.json, fields=['email', 'username', 'password', 'name', 'phone'])
    validate_email(email)
    validate_username(username)
    validate_length(username, 3, 32, fieldName='Username')
    validate_length(password, 6, 32, fieldName='Password')

    if User.objects(email=request.json.get('email')).first():
        return bad_request('Email already registered.')
    if User.objects(username=request.json.get('username')).first():
        return bad_request('Username already registered.')

    try:
        user = User.from_json(request.json)
        user.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    # send a email to confirm the account
    token = user.generate_confirmation_token()
    # send_email(user.email, 'Confirm Your Account',
    #            'auth/email/confirm', user=user, token=token)
    return jsonify(user.to_json()), 201, \
        {'Location': url_for('api.get_user', id=user.id)}


@api.route('/users/<id>', methods=['DELETE'])
# @http_auth.login_required
def delete_user(id):
    ''' 删除用户，并级联删除相关的Task '''
    try:
        user = User.objects(id=id).first()
    except:
        abort(404)

    if not user:
        abort(404)

    if hasattr(g, 'current_user') and user == g.current_user:
        return bad_request('Can not delete current user.')
    
    # 删除关联的task
    Task.objects(recorder=user).delete()

    msg = 'User %s have been removed.' % user.username
    user.delete()
    response = jsonify({'info': msg})
    response.status_code = 200
    return response


@api.route('/users/<id>', methods=['PUT'])
# @http_auth.login_required
# @admin_required
def edit_user(id):
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')

    user = User.objects(id=id).first()
    if user is None:
        abort(404)

    validate_require(request.json, fields=['email', 'username', 'password', 'name', 'admin', 'confirmed'])

    new_email = request.json.get('email')
    new_username = request.json.get('username')

    # 用户名不允许修改
    if user.username != new_username:
        return bad_request('Username can not modify.')

    # 若更改了邮箱，检查新邮箱是否已经注册，并将确认字段'confirmed'重置
    if user.email != new_email:
        validate_email(new_email)  # 格式验证
        if User.objects(email=new_email).first():
            return bad_request('The input email already registered.')
        self.confirmed = False

    user.email = new_email
    user.username = new_username
    user.name = request.json.get('name')
    user.phone = request.json.get('phone')
    user.admin = bool(request.json.get('admin'))
    user.confirmed = bool(request.json.get('confirmed'))
    try:
        user.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))

    # 若用户邮箱没有确认（邮箱变更），则重新发送确认邮件。
    if not user.confirmed:
        token = user.generate_confirmation_token()
        # send_email(user.email, 'Confirm Your Account',
        #            'auth/email/confirm', user=user, token=token)

    return jsonify(user.to_json())


@api.route('/users/change-password/', methods=['PUT'])
@http_auth.login_required
def change_password():
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')
        
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')

    validate_length(new_password, 6, 32, fieldName='Password')

    if not g.current_user.verify_password(old_password):
        return bad_request('The old password not matched.')

    g.current_user.password = new_password
    try:
        g.current_user.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    return jsonify({'message': 'Password changed.'})


@api.route('/users/search/')
def search_users():
    ''' 根据关键字检索用户，输入参数为filter，匹配字段包括email, username, name '''
    page = request.args.get('page', 1, type=int)
    match = request.args.get('match', '', type=str)

    if not match:  # 没有输入匹配条件，查询所有
        try:
            pagination = User.objects().paginate(page=page, per_page=10)
        except:
            return resource_not_found('Resource not found, please check your url or parameter.')

    import re
    from mongoengine.queryset.visitor import Q
    regex = re.compile('.*' + match + '.*')

    try:
        pagination = User.objects(Q(email=regex) | Q(username=regex) | Q(name=regex)).paginate(page=page, per_page=10)
    except:
        return resource_not_found('Resource not found, please check your url or parameter.')
    
    users = pagination.items

    prev = None
    if pagination.has_prev:
        prev = url_for('api.search_users', page=page - 1, match=match)
    next = None
    if pagination.has_next:
        next = url_for('api.search_users', page=page + 1, match=match)
    return jsonify({
        'users': [user.to_json() for user in users],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })
