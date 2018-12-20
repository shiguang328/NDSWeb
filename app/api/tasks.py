from datetime import datetime
from flask import jsonify, request, g, url_for, current_app, abort, redirect
from .. import db
from . import api
from .errors import bad_request, resource_not_found, TimestampError
from .authentication import http_auth
from ..models import Task, Car, Driver
from flask_mongoengine import ValidationError
from mongoengine.queryset.visitor import Q


@api.route('/tasks/')
# @auth.login_required
def get_tasks():
    page = request.args.get('page', 1, type=int)
    end_time = request.args.get('end_time', None, type=datetime)

    pagination = Task.objects.paginate(page=page, per_page=10)
    tasks = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_tasks', page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_tasks', page=page + 1)
    return jsonify({
        'tasks': [task.to_json() for task in tasks],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/tasks/<id>')
# @auth.login_required
def get_task(id):
    try:
        task = Task.objects(id=id).first()
    except:
        abort(404)

    if task:
        return jsonify(task.to_json())
    else:
        abort(404)


@api.route('/tasks/', methods=['POST'])
# @auth.login_required
def new_task():
    task = Task.from_json(request.json)
    task.save()
    return jsonify(task.to_json()), 201, \
        {'Location': url_for('api.get_task', id=task.id)}


@api.route('/tasks/<id>', methods=['PUT'])
# @auth.login_required
def edit_task(id):
    try:
        task = Task.objects(id=id).first()
    except:
        abort(404)

    if task is None:
        abort(404)
    if request.json.get('car'):
        task.car = Car.objects(id=request.json.get('car')).first()
    if request.json.get('driver'):
        task.driver = Driver.objects(id=request.json.get('driver')).first()
    start_time = request.json.get('start_time')
    end_time = request.json.get('end_time')
    if start_time and start_time.isnumeric():
        task.start_time = datetime.fromtimestamp(int(start_time))
    if end_time and end_time.isnumeric():
        task.end_time = datetime.fromtimestamp(int(end_time))
    task.disk_number = request.json.get('disk_number')
    task.save()
    return jsonify(task.to_json())


# 解码输入参数，构建查询条件
def decode_search_condition(field, data):
    if data is None or data=="" or data=='""' or data=='NaN' or data=='null':
            return {}
    if field in ['car', 'driver']:
        return {field: data}
    elif field in ['minstart_time', 'maxstart_time', 'minend_time', 'maxend_time']:
        try:
            data = datetime.utcfromtimestamp(int(data))
        except OSError:
            raise TimestampError('utc timestamp out of range.')
        # 操作符转化为mongodbengine标准的
        mp = {'min': 'gte', 'max': 'lte'}
        operate = mp[field[:3]]
        # 拼接查询字段
        new_field = field[3:] + '__' + operate
        return {new_field: data.isoformat()}
    return {}


# 以原生拼接方式构建查询条件
def generate_query(args):
    from bson import ObjectId
    query = {}
    for key, val in args.items():
        if val is None or val=="" or val=='""':
            continue
        if key == 'is_return':
            if val == '0':
                query[key] = False
            elif val == '1':
                query[key] = True
        elif key in ['car', 'driver']:
            query[key] = ObjectId(val)
        elif key in ['minstart_time', 'maxstart_time', 'minend_time', 'maxend_time']:
            data = datetime.utcfromtimestamp(int(val))
            mp = {'min': '$gte', 'max': '$lte'}
            operate = mp[key[:3]]
            field = key[3:]
            if field in query:
                query[field].update({operate: data})
            else:
                query[field] = {operate: data}
    return query


# http://127.0.0.1:5000/api/v1/tasks/search/
# ?page=2&is_return=0&car=""&driver=""&minstart_time=""&maxstart_time=""&minend_time=""&maxend_time=""
@api.route('/tasks/search/')
def search_tasks():
    args = request.args
    page = args.get('page', 1, type=int)
    is_return = args.get('is_return', 0, type=int)

    new_args = args.to_dict()
    if 'page' in new_args:
        new_args.pop('page')
    conditions = {}
    fields = ['is_return', 'car', 'driver', 'minstart_time', 'maxstart_time', 'minend_time', 'maxend_time']
    for key, value in new_args.items():
        # 参数检查
        if key not in fields:
            return bad_request('Parameter error.')
        # is_return定义：0:车辆未返回，即'end_time'为空；1：车辆已返回，即'end_time'不为空
        if key == 'is_return':
            if value == '0':
                conditions.update({'is_return': None})
            elif value == '1':
                conditions.update({'is_return': True})
            continue

        try:
            condition = decode_search_condition(key, value)
        except TimestampError as err:
            return bad_request(str(err))

        conditions.update(condition)
    # print('---------------------------conditions------------------------------')
    # print(conditions)
    try:
        pagination = Task.objects(**conditions).paginate(page=page, per_page=10)
    except:
        return resource_not_found('Resource not found, please check your url or parameter.')
    tasks = pagination.items

    # query = generate_query(new_args)
    # print('---------------------------query------------------------------')
    # print(query)
    # pagination = Task.objects(__raw__=query).paginate(page=page, per_page=10)
    # tasks = pagination.items

    prev = None
    if pagination.has_prev:
        prev = url_for('api.search_tasks', page=page - 1, **new_args)
    next = None
    if pagination.has_next:
        next = url_for('api.search_tasks', page=page + 1, **new_args)
    return jsonify({
        'tasks': [task.to_json() for task in tasks],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })