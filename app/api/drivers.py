from datetime import datetime
from flask import jsonify, request, g, url_for, current_app, abort
from .. import db
from . import api
from .errors import bad_request, resource_not_found, TimestampError
from .authentication import http_auth
from ..models import Driver, Task
from flask_mongoengine import ValidationError


@api.route('/drivers/')
# @http_auth.login_required
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
# @http_auth.login_required
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
# @http_auth.login_required
def new_driver():
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')
    try:
        driver = Driver.from_json(request.json)
        driver.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    return jsonify(driver.to_json()), 201, \
        {'Location': url_for('api.get_driver', id=driver.id)}


@api.route('/drivers/<id>', methods=['DELETE'])
# @http_auth.login_required
def delete_driver(id):
    ''' 删除司机，并级联删除相关的Task '''
    try:
        driver = Driver.objects(id=id).first()
    except:
        abort(404)

    if not driver:
        abort(404)
    
    # 删除关联的task
    Task.objects(driver=driver).delete()

    msg = 'Driver %s have been removed.' % driver.Name
    # print(msg)
    driver.delete()
    response = jsonify({'info': msg})
    response.status_code = 200
    return response


@api.route('/drivers/<id>', methods=['PUT'])
# @http_auth.login_required
def edit_driver(id):
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')

    driver = Driver.objects(id=id).first()
    if driver is None:
        abort(404)
    birthday = request.json.get('BirthDay')
    if birthday:
        driver.BirthDay = datetime.utcfromtimestamp(int(birthday))
    driver.Name = request.json.get('Name')
    driver.Address = request.json.get('Address')
    driver.City = request.json.get('City')
    driver.State = request.json.get('State')
    driver.Zip = request.json.get('Zip')
    driver.Gender = request.json.get('Gender')
    driver.DrivingYears = request.json.get('DrivingYears')
    driver.Profession = request.json.get('Profession')
    driver.MileageTotal = request.json.get('MileageTotal')
    try:
        driver.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    return jsonify(driver.to_json())


@api.route('/drivers/search/')
def search_drivers():
    page = request.args.get('page', 1, type=int)
    driverId = request.args.get('DriverId', '', type=str)
    name = request.args.get('Name', '', type=str)

    new_args = request.args.to_dict()
    if 'page' in new_args:
        new_args.pop('page')
    conditions = {}
    if driverId and driverId != '':
        conditions['DriverId'] = driverId
    if name and name != '':
        import re
        regex = re.compile('.*' + name + '.*')
        conditions['Name'] = regex
    
    try:
        pagination = Driver.objects(**conditions).paginate(page=page, per_page=10)
    except:
        return resource_not_found('Resource not found, please check your url or parameter.')
    drivers = pagination.items

    prev = None
    if pagination.has_prev:
        prev = url_for('api.search_drivers', page=page - 1, **new_args)
    next = None
    if pagination.has_next:
        next = url_for('api.search_drivers', page=page + 1, **new_args)
    return jsonify({
        'drivers': [driver.to_json() for driver in drivers],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/drivers/questionnaire/<id>', methods=['POST'])
def update_questionnaire(id):
    if not hasattr(request, 'json'):
        return bad_request('No json data recived.')
        
    questionnaire = request.json.get('questionnaire')
    # print(questionnaire)
    if not isinstance(questionnaire, dict):
        return bad_request('json parameter error.')
    # print(questionnaire)
    driver = Driver.objects(id=id).first()
    driver.Questionnaire = questionnaire
    try:
        driver.save()
    except Exception as why:
        current_app.logger.error(str(why))
        return bad_request(str(why))
    return jsonify(driver.to_json())