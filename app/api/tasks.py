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
# @http_auth.login_required
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
# @http_auth.login_required
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
# @http_auth.login_required
def new_task():
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')
    try:
        task = Task.from_json(request.json)
        if task.end_time:
            task.is_return = True
        task.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    return jsonify(task.to_json()), 201, \
        {'Location': url_for('api.get_task', id=task.id)}


@api.route('/tasks/<id>', methods=['DELETE'])
# @http_auth.login_required
def delete_task(id):
    try:
        task = Task.objects(id=id).first()
    except:
        abort(404)

    if not task:
        abort(404)

    msg = 'Task have been removed.'
    # print(msg)
    task.delete()
    response = jsonify({'info': msg})
    response.status_code = 200
    return response


@api.route('/tasks/<id>', methods=['PUT'])
# @http_auth.login_required
def edit_task(id):
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')
        
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
    if start_time:
        task.start_time = datetime.utcfromtimestamp(int(start_time))
    if end_time:
        task.end_time = datetime.utcfromtimestamp(int(end_time))
    task.disk_number = request.json.get('disk_number')

    if task.end_time:
        task.is_return = True
    try:
        task.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
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
            if value == 'false':
                conditions.update({'is_return': False})
            elif value == 'true':
                conditions.update({'is_return': True})
            continue

        try:
            condition = decode_search_condition(key, value)
        except TimestampError as err:
            return bad_request(str(err))

        conditions.update(condition)

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

import random
from .ghost_car import get_current_pos
cars = []
drivers = []
@api.route('/tasks/online/')
def online_tasks():
    # random select 5 car
    if not len(cars):
        cs = Car.objects()
        for i in range(5):
            car = random.choice(cs)
            cars.append(car)
        # cars.extend(random.sample(cs, 5))
    if not len(drivers):
        drs = Driver.objects()
        for i in range(5):
            driver = random.choice(drs)
            drivers.append(driver)
        # drivers.extend(random.sample(drs, 5))

    positions = get_current_pos()
    targets = []
    for i, pos in enumerate(positions):
        json_task = {}
        json_task['car'] = {'LicensePlate': cars[i].LicensePlate, 'url': url_for('api.get_car', id=cars[i].id)}
        json_task['driver'] = {'Name': drivers[i].Name, 'url': url_for('api.get_driver', id=drivers[i].id)}
        json_task['position'] = pos
        targets.append(json_task)

    return jsonify({
        'tasks': targets,
        'count': len(targets)
    })
