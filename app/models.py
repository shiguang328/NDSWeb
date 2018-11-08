from datetime import datetime
from random import randint
import hashlib
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from . import db, login_manager
from flask_mongoengine.wtf import model_form


class User(UserMixin, db.Document):
    email = db.StringField(required=True)
    username = db.StringField(required=True, max_length=50)
    admin = db.BooleanField(default=False)
    password_hash = db.StringField(required=True)
    confirmed = db.BooleanField(default=False)  # 邮箱是否确认
    name = db.StringField(required=True)
    phone = db.StringField()

    def __init__(self, **kwargs):
        ''' 注册用户是赋予角色，首先判断是否为管理员（配置中的FLASKY_ADMIN保存的电子邮件识别），
        只要这个邮箱在请求中出现，就赋予管理员角色，否则赋予默认角色。
        '''
        super(User, self).__init__(**kwargs)
        if self.email == current_app.config['FLASKY_ADMIN']:
            self.admin = True

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        ''' 通过用户id生成一个令牌（一般用于发送邮箱确认链接），有效期默认为一个小时 '''
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': str(self.id)}).decode('utf-8')

    def confirm(self, token):
        ''' 校验令牌，通过则返回True，并把数据库中的confirmed字段设为True '''
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != str(self.id):  # 判断id是否匹配
            return False
        self.confirmed = True
        self.save()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': str(self.id)}).decode('utf-8')

    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        # user = User.query.get(data.get('reset'))
        user = User.objects(id=ObjectId(data.get('reset')))
        if len(user) != 1:
            return False
        user = user[0]
        user.password_hash = generate_password_hash(new_password)
        # db.session.add(user)
        user.save()
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps(
            {'change_email': str(self.id), 'new_email': new_email}).decode('utf-8')

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != str(self.id):
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        # if self.query.filter_by(email=new_email).first() is not None:
        if len(User.objects(email=new_email)):
            return False
        self.email = new_email
        # self.avatar_hash = self.gravatar_hash()
        # db.session.add(self)
        self.save()  # add by leo
        return True

    # def can(self, perm):
    #     return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.admin

    def ping(self):
        # self.last_seen = datetime.utcnow()
        # db.session.add(self)
        self.save()

    # def gravatar_hash(self):
    #     return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    # def gravatar(self, size=100, default='identicon', rating='g'):
    #     url = 'https://secure.gravatar.com/avatar'
    #     hash = self.avatar_hash or self.gravatar_hash()
    #     return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
    #         url=url, hash=hash, size=size, default=default, rating=rating)

    # def to_json(self):
    #     json_user = {
    #         'url': url_for('api.get_user', email=self.email),
    #         'username': self.username,
    #         'member_since': self.member_since,
    #         'last_seen': self.last_seen,
    #         'posts_url': url_for('api.get_user_posts', id=self.id),
    #         'followed_posts_url': url_for('api.get_user_followed_posts',
    #                                       id=self.id),
    #         'post_count': self.posts.count()
    #     }
    #     return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': str(self.id)}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        user = User.objects(id=ObjectId(data['id']))
        if not len(user):
            return None
        return user[0]

    def __repr__(self):
        return '<User %r>' % self.username

    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     admin=True,
                     password_hash=generate_password_hash(forgery_py.lorem_ipsum.word()),
                     confirmed=True,
                     name=forgery_py.name.full_name())
                    #  phone=forgery_py.lorem_ipsum.word())
            u.save()


# AnonymousUserMixin has the following properties and methods:
# 1. is_active and is_authenticated are False
# 2. is_anonymous is True
# 3. get_id() return None
class AnonymousUser(AnonymousUserMixin):
    ''' 该类继承自Flask-Login中的AnonymousUserMixin，并将其设为用户未登陆时的current_user值，
    这样程序不用先检查用户是否登陆，就能够自由调用current_user.can()和current_user.is_administrator()
    方法。
    '''
    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    ''' Falsk-Login要求程序实现一个回调函数，使用指定的标识符（特征）从数据库加载用户
    此处使用用户id加载
    如果找到用户，必须返回用户Object，否则返回None
    '''
    user = User.objects(id=user_id)
    print('load_user: user_id = ', user_id)
    print('user: ', user)
    if not len(user):
        return None
    return user[0]


class Car(db.Document):
    CarId = db.StringField(required=True)
    LicensePlate = db.StringField(required=True)
    Brand = db.StringField()
    OwnerCompany = db.StringField()
    Project = db.StringField()
    BuyTime = db.DateTimeField()
    InsuranceNumber = db.StringField()
    ModelName = db.StringField()
    VehicleType = db.StringField()
    PowerType = db.StringField()
    AutonomousVehicle = db.BooleanField()
    AccidentLog = db.StringField()
    Others = db.StringField()

    def __init__(self, **kwargs):
        super(Car, self).__init__(**kwargs)
        # 生成一个随机的CarId
        while not self.CarId:
            temp = str(randint(10000000, 99999999))  # 获取随机数
            if not len(Car.objects(CarId=temp)):  # 检查数据库中是否重复
                self.CarId = temp

    def to_json(self):
        json_car = {
            'url': url_for('api.get_car', id=self.id),
            'CarId': self.CarId,
            'LicensePlate': self.LicensePlate,
            'Brand': self.Brand,
            'OwnerCompany': self.OwnerCompany,
            'Project': self.Project,
            'BuyTime': self.BuyTime,
            'InsuranceNumber': self.InsuranceNumber,
            'ModelName': self.ModelName,
            'VehicleType': self.VehicleType,
            'PowerType': self.PowerType,
            'AutonomousVehicle': self.AutonomousVehicle,
            'AccidentLog': self.AccidentLog,
            'Others': self.Others
        }
        return json_car

    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            c = Car(CarId=forgery_py.lorem_ipsum.word(),
                    LicensePlate=forgery_py.lorem_ipsum.word())
            c.save()


class Driver(db.Document):
    DriverId = db.StringField(required=True)
    FirstName = db.StringField(required=True)
    LastName = db.StringField()
    Address = db.StringField()
    City = db.StringField()
    State = db.StringField()
    Zip = db.StringField()
    Gender = db.StringField()
    Location = db.StringField()
    BirthDay = db.DateTimeField()
    Vehicle = db.ReferenceField(Car)  # reference field
    DrivingYears = db.IntField(required=True)
    Profession = db.StringField()
    MileageTotal = db.StringField()

    def __init__(self, **kwargs):
        super(Driver, self).__init__(**kwargs)
        while not self.DriverId:
            temp = str(randint(10000000, 99999999))  # 获取随机数
            if not len(Driver.objects(DriverId=temp)):  # 检查数据库中是否重复
                self.DriverId = temp

    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py
        from random import choice

        seed()
        for i in range(count):
            cars = Car.objects()
            car = choice(cars)
            d = Driver(DriverId=forgery_py.lorem_ipsum.word(),
                    FirstName=forgery_py.lorem_ipsum.word(),
                    Vehicle=car,
                    DrivingYears=randint(10000000, 99999999))
            d.save()
