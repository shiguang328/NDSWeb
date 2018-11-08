from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from ..models import Car
from flask_mongoengine import ValidationError


@api.route('/cars/')
def get_cars():
    page = request.args.get('page', 1, type=int)
    pagination = Car.objects.paginate(page=page, per_page=10)
    cars = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_cars', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_cars', page=page+1)
    return jsonify({
        'cars': [car.to_json() for car in cars],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/cars/<id>')
def get_car(id):
    try:
        car = Car.objects(id=id).first()
    except:
        abort(404)

    if car:
        return jsonify(car.to_json())
    else:
        abort(404)