from datetime import datetime
from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .authentication import http_auth
from ..models import Car
from .errors import bad_request, resource_not_found, TimestampError
from flask_mongoengine import ValidationError


@api.route('/cars/')
# @auth.login_required
def get_cars():
    page = request.args.get('page', 1, type=int)
    pagination = Car.objects.paginate(page=page, per_page=10)
    cars = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_cars', page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_cars', page=page + 1)
    return jsonify({
        'cars': [car.to_json() for car in cars],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/cars/dropdown/')
def get_cars_dropdown():
    cars = Car.objects()
    return jsonify({
        'cars': [car.to_simple_json() for car in cars]
    })

@api.route('/cars/projects/')
def get_projects():
    projects = Car.all_projects()
    return jsonify({
        'projects': projects
    })


@api.route('/cars/<id>')
# @auth.login_required
def get_car(id):
    try:
        car = Car.objects(id=id).first()
    except:
        abort(404)

    if car:
        return jsonify(car.to_json())
    else:
        abort(404)


@api.route('/cars/', methods=['POST'])
# @auth.login_required
def new_car():
    licensePlate = request.json.get('LicensePlate')
    if not licensePlate:
        return bad_request('License plate not provided.')
    if Car.objects(LicensePlate=licensePlate).first():
        return bad_request('License plate already registered.')
        
    car = Car.from_json(request.json)
    car.save()
    return jsonify(car.to_json()), 201, \
        {'Location': url_for('api.get_car', id=car.id)}


@api.route('/cars/<id>', methods=['PUT'])
# @auth.login_required
def edit_car(id):
    car = Car.objects(id=id).first()
    if car is None:
        abort(404)
    buytime = request.json.get('BuyTime')
    if buytime:
        car.BuyTime = datetime.fromtimestamp(int(buytime))
    car.LicensePlate = request.json.get('LicensePlate')
    car.Brand = request.json.get('Brand')
    car.OwnerCompany = request.json.get('OwnerCompany')
    car.Project = request.json.get('Project')
    # car.BuyTime = request.json.get('BuyTime')
    car.InsuranceNumber = request.json.get('InsuranceNumber')
    car.ModelName = request.json.get('ModelName')
    car.VehicleType = request.json.get('VehicleType')
    car.PowerType = request.json.get('PowerType')
    car.AutonomousVehicle = request.json.get('AutonomousVehicle')
    car.AccidentLog = request.json.get('AccidentLog')
    car.Others = request.json.get('Others')
    car.save()
    return jsonify(car.to_json())


# http://127.0.0.1:5000/api/v1/cars/search/?page=2&CarId=&LicensePlate=&Project=&minBuyTime=&maxBuyTime=
@api.route('/cars/search/')
def search_cars():
    args = request.args
    page = args.get('page', 1, type=int)

    new_args = args.to_dict()
    if 'page' in new_args:
        new_args.pop('page')
    conditions = {}
    fields = ['CarId', 'LicensePlate', 'Project', 'minBuyTime', 'maxBuyTime']
    for key, value in new_args.items():
        # 参数检查
        if key not in fields:
            return bad_request('Parameter error.')
        try:
            condition = decode_search_condition(key, value)
        except TimestampError as err:
            return bad_request(str(err))

        conditions.update(condition)

    try:
        pagination = Car.objects(**conditions).paginate(page=page, per_page=10)
    except:
        return resource_not_found('Resource not found, please check your url or parameter.')
    cars = pagination.items

    prev = None
    if pagination.has_prev:
        prev = url_for('api.search_cars', page=page - 1, **new_args)
    next = None
    if pagination.has_next:
        next = url_for('api.search_cars', page=page + 1, **new_args)
    return jsonify({
        'cars': [car.to_json() for car in cars],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


# 解码输入参数，构建查询条件
def decode_search_condition(field, data):
    if data is None or data=="" or data=='""' or data=='NaN' or data=='null':
            return {}
    if field in ['CarId', 'LicensePlate', 'Project']:
        return {field: data}
    elif field in ['minBuyTime', 'maxBuyTime']:
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