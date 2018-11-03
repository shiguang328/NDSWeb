from flask import jsonify, request, g, url_for, current_app
from .. import db
from . import api


# @api.route('/cars/')
# def get_cars():
#     page = request.args.get('page', 1, type=int)
#     pagination = Post.query.paginate(
#         page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
#         error_out=False)
#     posts = pagination.items
#     prev = None
#     if pagination.has_prev:
#         prev = url_for('api.get_posts', page=page-1)
#     next = None
#     if pagination.has_next:
#         next = url_for('api.get_posts', page=page+1)
#     return jsonify({
#         'posts': [post.to_json() for post in posts],
#         'prev': prev,
#         'next': next,
#         'count': pagination.total
#     })