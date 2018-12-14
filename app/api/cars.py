from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .authentication import auth
from ..models import Car
from .errors import bad_request
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
    car.LicensePlate = request.json.get('LicensePlate')
    car.Brand = request.json.get('Brand')
    car.OwnerCompany = request.json.get('OwnerCompany')
    car.Project = request.json.get('Project')
    car.BuyTime = request.json.get('BuyTime')
    car.InsuranceNumber = request.json.get('InsuranceNumber')
    car.ModelName = request.json.get('ModelName')
    car.VehicleType = request.json.get('VehicleType')
    car.PowerType = request.json.get('PowerType')
    car.AutonomousVehicle = request.json.get('AutonomousVehicle')
    car.AccidentLog = request.json.get('AccidentLog')
    car.Others = request.json.get('Others')
    car.save()
    return jsonify(car.to_json())