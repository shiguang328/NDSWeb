from flask import jsonify, request, g, url_for, current_app
from flask_restful import reqparse, abort, Api, Resource
from .. import db


# class User(Resource):
#     def get(self, username):
#         if username is None or username == '':
#             return '', 404
#         user = db.users.find_one({'username': username})
#         if user is None:
#             return '', 404
#         user.pop('_id')
#         return user

#     def put(self):
#         args = reqparse.RequestParser().parse_args()
#         db.users.insert_one(args)