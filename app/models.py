from datetime import datetime
from random import randint
import hashlib
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin, current_user
from . import db, login_manager
from flask_mongoengine.wtf import model_form
from app.exceptions import ValidationError


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
        user = User.objects(id=ObjectId(data.get('reset')))
        if len(user) != 1:
            return False
        user = user[0]
        user.password_hash = generate_password_hash(new_password)
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
        if User.objects(email=new_email).first() is not None:
            return False
        self.email = new_email
        # self.avatar_hash = self.gravatar_hash()
        self.save()  # add by leo
        return True

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
        print('recive token: ', token)
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
            print(data)
        except:
            return None
        user = User.objects(id=ObjectId(data['id'])).first()
        return user

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
    def from_json(json_car):
        LicensePlate = json_car.get('LicensePlate')
        Brand = json_car.get('Brand')
        OwnerCompany = json_car.get('OwnerCompany')
        Project = json_car.get('Project')
        BuyTime = json_car.get('BuyTime')
        InsuranceNumber = json_car.get('InsuranceNumber')
        ModelName = json_car.get('ModelName')
        VehicleType = json_car.get('VehicleType')
        PowerType = json_car.get('PowerType')
        AutonomousVehicle = json_car.get('AutonomousVehicle')
        AccidentLog = json_car.get('AccidentLog')
        Others = json_car.get('Others')

        if LicensePlate is None or LicensePlate == '':
            raise ValidationError('car does not have a license plate')
        return Car(LicensePlate=LicensePlate,
                   Brand=Brand,
                   OwnerCompany=OwnerCompany,
                   Project=Project,
                   BuyTime=BuyTime,
                   InsuranceNumber=InsuranceNumber,
                   ModelName=ModelName,
                   VehicleType=VehicleType,
                   PowerType=PowerType,
                   AutonomousVehicle=AutonomousVehicle,
                   AccidentLog=AccidentLog,
                   Others=Others)

    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            c = Car(LicensePlate=forgery_py.lorem_ipsum.word())
            c.save()


class Driver(db.Document):
    DriverId = db.StringField(required=True)
    Name = db.StringField()
    # FirstName = db.StringField()
    # LastName = db.StringField()
    Address = db.StringField()
    City = db.StringField()
    State = db.StringField()
    Zip = db.StringField()
    Gender = db.StringField()
    Location = db.StringField()
    BirthDay = db.DateTimeField()
    DrivingYears = db.IntField()
    Profession = db.StringField()
    MileageTotal = db.StringField()

    def __init__(self, **kwargs):
        super(Driver, self).__init__(**kwargs)
        while not self.DriverId:
            temp = str(randint(10000000, 99999999))  # 获取随机数
            if not len(Driver.objects(DriverId=temp)):  # 检查数据库中是否重复
                self.DriverId = temp

    def to_json(self):
        json_driver = {
            'url': url_for('api.get_driver', id=self.id),
            # 'FirstName': self.FirstName,
            # 'LastName': self.LastName,
            'Name': self.Name,
            'Address': self.Address,
            'City': self.City,
            'State': self.State,
            'Zip': self.Zip,
            'Gender': self.Gender,
            'Location': self.Location,
            'BirthDay': self.BirthDay,
            'DrivingYears': self.DrivingYears,
            'Profession': self.Profession,
            'MileageTotal': self.MileageTotal
        }
        return json_driver

    @staticmethod
    def from_json(json_driver):
        # FirstName = json_driver.get('FirstName')
        # LastName = json_driver.get('LastName')
        Name = json_driver.get('Name')
        Address = json_driver.get('Address')
        City = json_driver.get('City')
        State = json_driver.get('State')
        Zip = json_driver.get('Zip')
        Gender = json_driver.get('Gender')
        Location = json_driver.get('Location')
        BirthDay = json_driver.get('BirthDay')
        DrivingYears = json_driver.get('DrivingYears')
        Profession = json_driver.get('Profession')
        MileageTotal = json_driver.get('MileageTotal')
        if Name is None or Name == '':
            raise ValidationError('driver does not have a name')
        return Driver(Name=Name,
                      Address=Address,
                      City=City,
                      State=State,
                      Zip=Zip,
                      Gender=Gender,
                      Location=Location,
                      BirthDay=BirthDay,
                      DrivingYears=DrivingYears,
                      Profession=Profession,
                      MileageTotal=MileageTotal)

    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            d = Driver(DriverId=forgery_py.lorem_ipsum.word(),
                    Name=forgery_py.lorem_ipsum.word(),
                    DrivingYears=randint(10000000, 99999999))
            d.save()

    @staticmethod
    def merge_firstname_lastname_to_name():
        ''' 将FirstName和LastName融合为Name，然后删除原先字段 '''
        drivers = Driver.objects()
        for driver in drivers:
            if driver.Name is None:
                name = ''
                if driver.FirstName:
                    name = name + driver.FirstName
                if driver.LastName:
                    if name == '':
                        name = driver.LastName
                    else:
                        name = name + ' ' + driver.LastName
                driver.Name = name
                driver.save()
            else:
                if hasattr(driver, 'FirstName'):
                    delattr(driver, 'FirstName')
                if hasattr(driver, 'LastName'):
                    delattr(driver, 'LastName')
                driver.save()


class Trip(db.Document):
    car = db.ReferenceField(Car, required=True)
    driver = db.ReferenceField(Driver, required=True)
    start_time = db.DateTimeField(required=True)
    end_time = db.DateTimeField()
    disk_number = db.StringField()
    recorder = db.ReferenceField(User)

    def __init__(self, **kwargs):
        super(Trip, self).__init__(**kwargs)
        if current_user.is_authenticated:
            self.recorder = current_user

    def to_json(self):
        json_trip = {
            'url': url_for('api.get_trip', id=self.id),
            'start_time': self.start_time,
            'end_time': self.end_time,
            'disk_number': self.disk_number
        }
        if self.car:
            json_trip['car'] = {'LicensePlate': self.car.LicensePlate, 'url': url_for('api.get_car', id=self.car.id)}
        if self.driver:
            json_trip['driver'] = {'Name': self.driver.Name, 'url': url_for('api.get_driver', id=self.driver.id)}
        if self.recorder:
            json_trip['recorder'] = self.recorder.name
        return json_trip

    def from_json(self, json_trip):
        ''' 前端发送car和driver的id来匹配Car和Driver对象 '''
        if not json_trip.get('start_time'):
            raise ValidationError('trip does not have a start time')
        if not json_trip.get('car'):
            raise ValidationError('trip does not have a car')
        if not json_trip.get('driver'):
            raise ValidationError('trip does not have a driver')
        car = Car.objects(id=ObjectId(json_trip.get('car'))).first()
        if not car:
            raise ValidationError('input car not found')
        driver = Driver.objects(id=ObjectId(json_trip.get('driver'))).first()
        if not driver:
            raise ValidationError('input driver not found')
        recorder = None
        if current_user.is_authenticated:
            recorder = current_user
        trip = Trip(start_time=json_trip.get('start_time'),
                    car=car,
                    driver=driver,
                    recorder=recorder)
        return trip
        
    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py
        from random import choice

        cars = Car.objects()
        drivers = Driver.objects()

        seed()
        for i in range(count):
            car = choice(cars)
            driver = choice(drivers)

            trip = Trip(car=car,
                        driver=driver,
                        start_time=forgery_py.date.date(True))
            trip.save()
