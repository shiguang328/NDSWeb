from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .authentication import auth
from ..models import Driver
from flask_mongoengine import ValidationError


@api.route('/drivers/')
# @auth.login_required
def get_drivers():
    page = request.args.get('page', 1, type=int)
    pagination = Driver.objects.paginate(page=page, per_page=10)
    drivers = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_drivers', page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_drivers', page=page + 1)
    return jsonify({
        'drivers': [driver.to_json() for driver in drivers],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/drivers/dropdown/')
def get_drivers_dropdown():
    drivers = Driver.objects()
    return jsonify({
        'drivers': [driver.to_simple_json() for driver in drivers]
    })


@api.route('/drivers/<id>')
# @auth.login_required
def get_driver(id):
    try:
        driver = Driver.objects(id=id).first()
    except:
        abort(404)

    if driver:
        return jsonify(driver.to_json())
    else:
        abort(404)


@api.route('/drivers/', methods=['POST'])
# @auth.login_required
def new_driver():
    driver = Driver.from_json(request.json)
    driver.save()
    return jsonify(driver.to_json()), 201, \
        {'Location': url_for('api.get_driver', id=driver.id)}


@api.route('/drivers/<id>', methods=['PUT'])
# @auth.login_required
def edit_driver(id):
    driver = Driver.objects(id=id).first()
    if driver is None:
        abort(404)
    driver.FirstName = request.json.get('FirstName')
    driver.LastName = request.json.get('LastName')
    driver.Address = request.json.get('Address')
    driver.City = request.json.get('City')
    driver.State = request.json.get('State')
    driver.Zip = request.json.get('Zip')
    driver.Gender = request.json.get('Gender')
    driver.Location = request.json.get('Location')
    driver.BirthDay = request.json.get('BirthDay')
    driver.DrivingYears = request.json.get('DrivingYears')
    driver.Profession = request.json.get('Profession')
    driver.MileageTotal = request.json.get('MileageTotal')
    driver.save()
    return jsonify(driver.to_json())
