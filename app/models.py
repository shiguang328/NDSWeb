from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from . import db
from flask_mongoengine.wtf import model_form


class User(UserMixin, db.Document):
    email = db.StringField(required=True)
    username = db.StringField(required=True, max_length=50)
    admin = db.BooleanField(default=False)
    password_hash = db.StringField(required=True)
    confirmed = db.BooleanField(default=False)  # 邮箱是否确认
    name = db.StringField(required=True)
    phone = db.StringField(required=True)

    def __init__(self, user_id, extras=None):
        self.id = user_id
        if extras is not None and isinstance(extras, dict):
            for name, val in extras.items():
                setattr(self, name, val)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        ''' 校验令牌，通过则返回True，并把数据库中的confirmed字段设为True '''
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirm = True
