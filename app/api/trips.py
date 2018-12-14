from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .authentication import auth
from ..models import Trip, Car, Driver
from flask_mongoengine import ValidationError


@api.route('/trips/')
# @auth.login_required
def get_trips():
    page = request.args.get('page', 1, type=int)
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
    trip.start_time = request.json.get('start_time')
    trip.end_time = request.json.get('end_time')
    trip.disk_number = request.json.get('disk_number')
    trip.save()
    return jsonify(trip.to_json())
    