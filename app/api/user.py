from flask import render_template, redirect, request, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from . import auth
from .errors import bad_request
from .. import db
from ..models import User
from ..email import send_email


@auth.route('/login/', methods=['POST'])
def login():
    print('find login view.')
    email = request.json.get('email')
    password = request.json.get('password')
    remember_me = request.json.get('remember_me')

    user = User.objects(email=email).first()
    if not user:
        return bad_request('Email not exist.')
    if not user.verify_password(password):
        return bad_request('Password error.')
    login_user(user, remember_me)
    return jsonify(user.to_json())