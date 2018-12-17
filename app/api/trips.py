from datetime import datetime
from flask import jsonify, request, g, url_for, current_app, abort, redirect
from .. import db
from . import api
from .errors import bad_request
from .authentication import auth
from ..models import Trip, Car, Driver
from flask_mongoengine import ValidationError
from mongoengine.queryset.visitor import Q


@api.route('/trips/')
# @auth.login_required
def get_trips():
    page = request.args.get('page', 1, type=int)
    end_time = request.args.get('end_time', None, type=datetime)

    pagination = Trip.objects.paginate(page=page, per_page=10)
    trips = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_trips', page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_trips', page=page + 1)
    return jsonify({
        'trips': [trip.to_json() for trip in trips],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/trips/<id>')
# @auth.login_required
def get_trip(id):
    try:
        trip = Trip.objects(id=id).first()
    except:
        abort(404)

    if trip:
        return jsonify(trip.to_json())
    else:
        abort(404)


@api.route('/trips/', methods=['POST'])
# @auth.login_required
def new_trip():
    trip = Trip.from_json(request.json)
    trip.save()
    return jsonify(trip.to_json()), 201, \
        {'Location': url_for('api.get_trip', id=trip.id)}


@api.route('/trips/<id>', methods=['PUT'])
# @auth.login_required
def edit_trip(id):
    try:
        trip = Trip.objects(id=id).first()
    except:
        abort(404)

    if trip is None:
        abort(404)
    if request.json.get('car'):
        trip.car = Car.objects(id=request.json.get('car')).first()
    if request.json.get('driver'):
        trip.driver = Driver.objects(id=request.json.get('driver')).first()
    start_time = request.json.get('start_time')
    end_time = request.json.get('end_time')
    if start_time and start_time.isnumeric():
        trip.start_time = datetime.fromtimestamp(int(start_time))
    if end_time and end_time.isnumeric():
        trip.end_time = datetime.fromtimestamp(int(end_time))
    # trip.start_time = request.json.get('start_time')
    # trip.end_time = request.json.get('end_time')
    trip.disk_number = request.json.get('disk_number')
    trip.save()
    return jsonify(trip.to_json())


def decode_search_condition(field, data):
    if ':' not in data:
        if 'time' in field:
            data = datetime.utcfromtimestamp(int(data))
        return {field: data}
    operator, data = data.split(':')
    field = field + '__' + operator
    if 'time' in field:
        data = datetime.utcfromtimestamp(int(data))
    return {field: data}
    

# /items?price=gte:10&price=lte:100
@api.route('/trips/search/')
def search_trips():
    args = request.args
    page = args.get('page', 1, type=int)
    new_args = args.to_dict()
    # print(new_args)
    if 'page' in new_args:
        new_args.pop('page')

    # 若无查找参数（page除外），重定向到get_trips
    if not len(new_args):
        return redirect(url_for('api.get_trips'))

    # fields = ['car', 'driver', 'start_time', 'end_time', 'disk_number', 'recorder']
    conditions = {}
    fields = ['car', 'driver', 'start_time', 'end_time']
    for key, value in new_args.items():
        if key not in fields:
            return bad_request('Parameter error.')
        condition = decode_search_condition(key, value)
        conditions.update(condition)
    # trips = Trip.objects(**conditions)
    pagination = Trip.objects(**conditions).paginate(page=page, per_page=10)
    trips = pagination.items

    prev = None
    if pagination.has_prev:
        prev = url_for('api.search_trips', page=page - 1, **new_args)
    next = None
    if pagination.has_next:
        next = url_for('api.search_trips', page=page + 1, **new_args)
    return jsonify({
        'trips': [trip.to_json() for trip in trips],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })

    return jsonify({
        'trips': [trip.to_json() for trip in trips]
    })