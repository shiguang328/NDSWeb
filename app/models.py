from datetime import datetime, timedelta
from random import randint
import hashlib
import calendar
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin, current_user
from . import db, login_manager
from flask_mongoengine.wtf import model_form
from app.exceptions import ValidationError


class User(UserMixin, db.Document):
    email = db.StringField(required=True, unique=True)
    username = db.StringField(required=True, unique=True, max_length=50)
    admin = db.BooleanField(default=False)
    password_hash = db.StringField(required=True)
    confirmed = db.BooleanField(default=False)  # 邮箱是否确认
    name = db.StringField(required=True)
    phone = db.StringField()
    member_since = db.DateTimeField(default=datetime.utcnow)
    last_seen = db.DateTimeField(default=datetime.utcnow)

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
        self.last_seen = datetime.utcnow()
        self.save()

    # def gravatar_hash(self):
    #     return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    # def gravatar(self, size=100, default='identicon', rating='g'):
    #     url = 'https://secure.gravatar.com/avatar'
    #     hash = self.avatar_hash or self.gravatar_hash()
    #     return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
    #         url=url, hash=hash, size=size, default=default, rating=rating)

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'email': self.email,
            'username': self.username,
            'admin': self.admin,
            'confirmed': self.confirmed,
            'name': self.name,
            'phone': self.phone,
            'member_since': datetime_to_timestamp(self.member_since),
            'last_seen': datetime_to_timestamp(self.last_seen)
        }
        return json_user

    @staticmethod
    def from_json(json_user):
        email = json_user.get('email')
        username = json_user.get('username')
        admin = json_user.get('admin')
        password = json_user.get('password')
        confirmed = json_user.get('confirmed')
        name = json_user.get('name')
        phone = json_user.get('phone')

        user = User(email=email,
                    username=username,
                    password_hash=generate_password_hash(password),
                    confirmed=confirmed,
                    admin=admin,
                    name=name,
                    phone=phone)
        return user
        

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': str(self.id)}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        # print('recive token: ', token)
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
            # print(data)
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
            u.save()

    @staticmethod
    def delete_user():
        for u in User.objects():
            if u.email not in ['496073473@qq.com', 'liuzhipeng@tongji.edu.cn']:
                u.delete()
                print('success delete user %s' % u.username)


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
    CarId = db.StringField(required=True, unique=True)
    LicensePlate = db.StringField(required=True)
    Brand = db.StringField()
    OwnerCompany = db.StringField()
    Project = db.StringField()
    BuyTime = db.DateTimeField()
    InsuranceNumber = db.StringField()
    ModelName = db.StringField()
    VehicleType = db.StringField()
    PowerType = db.StringField()
    AutonomousLevel = db.StringField()
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
            'BuyTime': datetime_to_timestamp(self.BuyTime),
            'InsuranceNumber': self.InsuranceNumber,
            'ModelName': self.ModelName,
            'VehicleType': self.VehicleType,
            'PowerType': self.PowerType,
            'AutonomousLevel': self.AutonomousLevel,
            'AccidentLog': self.AccidentLog,
            'Others': self.Others
        }
        return json_car

    def to_simple_json(self):
        json_car = {
            'LicensePlate': self.LicensePlate,
            'id': str(self.id)
        }
        return json_car

    @staticmethod
    def all_projects():
        projects = set()
        cars = Car.objects()
        for car in cars:
            if car.Project and car.Project != '':
                projects.add(car.Project)
        return sorted(list(projects))

    @staticmethod
    def from_json(json_car):
        buytime = json_car.get('BuyTime')
        if buytime:
            buytime = datetime.utcfromtimestamp(int(buytime))
        else:
            buytime = None
        LicensePlate = json_car.get('LicensePlate')
        Brand = json_car.get('Brand')
        OwnerCompany = json_car.get('OwnerCompany')
        Project = json_car.get('Project')
        BuyTime = buytime
        InsuranceNumber = json_car.get('InsuranceNumber')
        ModelName = json_car.get('ModelName')
        VehicleType = json_car.get('VehicleType')
        PowerType = json_car.get('PowerType')
        AutonomousLevel = json_car.get('AutonomousLevel')
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
                   AutonomousLevel=AutonomousLevel,
                   AccidentLog=AccidentLog,
                   Others=Others)

    @staticmethod
    def generate_fake(count=100):
        from random import seed, choice
        import forgery_py

        seed()
        brands = ['Audi', 'Toyota', 'Nissan', 'Buick', 'BMW', 'Cadillac']
        types = ['SUV', 'Van', 'Trucks', 'Bus', 'Taxi', 'Car']
        projects = ['华为项目', '宝马项目', 'VTTI项目', '通用项目']
        cha = ['A', 'B', 'C', 'D', 'E', 'H']
            
        for i in range(count):
            plate = None
            while not plate:
                num = str(randint(100000, 999999))  # 获取随机数
                candidate = '沪' + choice(cha) + str(num)
                if not Car.objects(LicensePlate=candidate).first():  # 检查数据库中是否重复
                    plate = candidate

            c = Car(LicensePlate=plate,
                    Brand=choice(brands),
                    Project=choice(projects),
                    VehicleType=choice(types),
                    BuyTime=forgery_py.date.date(True))
            c.save()

    @staticmethod
    def delete_all_car(condition=None):
        if not condition:
            return Car.objects().delete()


class Driver(db.Document):
    DriverId = db.StringField(required=True, unique=True)
    Name = db.StringField(required=True)
    Address = db.StringField()
    City = db.StringField()
    State = db.StringField()
    Zip = db.StringField()
    Gender = db.StringField()
    # Location = db.StringField()
    BirthDay = db.DateTimeField()
    DrivingYears = db.IntField()
    Profession = db.StringField()
    MileageTotal = db.StringField()
    Questionnaire = db.DictField()

    def __init__(self, **kwargs):
        super(Driver, self).__init__(**kwargs)
        while not self.DriverId:
            temp = str(randint(10000000, 99999999))  # 获取随机数
            if not len(Driver.objects(DriverId=temp)):  # 检查数据库中是否重复
                self.DriverId = temp

    def to_json(self):
        json_driver = {
            'DriverId': self.DriverId,
            'Name': self.Name,
            'url': url_for('api.get_driver', id=self.id),
            'Address': self.Address,
            'City': self.City,
            'State': self.State,
            'Zip': self.Zip,
            'Gender': self.Gender,
            # 'Location': self.Location,
            'BirthDay': datetime_to_timestamp(self.BirthDay),
            'DrivingYears': self.DrivingYears,
            'Profession': self.Profession,
            'MileageTotal': self.MileageTotal,
            'Questionnaire': self.Questionnaire
        }
        return json_driver

    def to_simple_json(self):
        json_driver = {
            'Name': self.Name,
            'id': str(self.id)
        }
        return json_driver

    @staticmethod
    def from_json(json_driver):
        birthday = json_driver.get('BirthDay')
        # print('before tansfer')
        # print(birthday)
        if birthday:
            birthday = datetime.utcfromtimestamp(int(birthday))
        else:
            birthday = None
        # print('after tansfer')
        # print(birthday)
        Name = json_driver.get('Name')
        Address = json_driver.get('Address')
        City = json_driver.get('City')
        State = json_driver.get('State')
        Zip = json_driver.get('Zip')
        Gender = json_driver.get('Gender')
        # Location = json_driver.get('Location')
        BirthDay = birthday
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
                    #   Location=Location,
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
            birthday = forgery_py.date.date(True)
            year = randint(20, 60)
            birthday = birthday + timedelta(-360*year)
            d = Driver(Name=forgery_py.name.full_name(),
                    DrivingYears=randint(0, 40),
                    Address=forgery_py.address.street_address(),
                    Zip=forgery_py.address.zip_code(),
                    City=forgery_py.address.city(),
                    State=forgery_py.address.state(),
                    BirthDay=birthday)
            d.save()

    @staticmethod
    def delete_all_drivers(condition=None):
        if not condition:
            drivers = Driver.objects()
            for i in range(len(drivers)):
                if int(drivers[i].DriverId) > 100000:
                    drivers[i].delete()

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


# class Questionnaire(db.EmbeddedDocument):
#     education_level = db.IntField()  # 1:小学 2:初/高中 3:大/中专 4:本科 5：研究生及以上
#     violation_last_year = db.IntField()  # 近一年违章数
#     accident_last_year = db.IntField()  # 近一年事故数
#     driving_frequency = db.IntField()  # 1:几乎不开车 2:一个月一次 3:一周一次 4:一周2到3次 5：每天驾驶
#     questions = db.ListFie


class Task(db.Document):
    car = db.ReferenceField(Car, required=True)
    driver = db.ReferenceField(Driver, required=True)
    start_time = db.DateTimeField(required=True)
    end_time = db.DateTimeField()
    is_return = db.BooleanField(default=False)
    disk_number = db.StringField()
    recorder = db.ReferenceField(User)

    def __init__(self, **kwargs):
        super(Task, self).__init__(**kwargs)
        if not self.recorder:
            if current_user and current_user.is_authenticated:
                self.recorder = current_user

    def to_json(self):
        # if self.start_time:
        #     start_time = calendar.timegm(self.start_time.utctimetuple())
        # else:
        #     start_time = None
        # if self.end_time:
        #     end_time = calendar.timegm(self.end_time.utctimetuple())
        # else:
        #     end_time = None
        json_task = {
            'url': url_for('api.get_task', id=self.id),
            'start_time': datetime_to_timestamp(self.start_time),
            'end_time': datetime_to_timestamp(self.end_time),
            # 'start_time': start_time,
            # 'end_time': end_time,
            'disk_number': self.disk_number,
            'is_return': bool(self.is_return)
        }
        if self.car:
            json_task['car'] = {'LicensePlate': self.car.LicensePlate, 'url': url_for('api.get_car', id=self.car.id)}
        if self.driver:
            json_task['driver'] = {'Name': self.driver.Name, 'url': url_for('api.get_driver', id=self.driver.id)}
        if self.recorder:
            json_task['recorder'] = self.recorder.name
        return json_task

    def from_json(json_task):
        ''' 前端发送car和driver的id来匹配Car和Driver对象 '''
        if not json_task.get('start_time'):
            raise ValidationError('task does not have a start time')
        if not json_task.get('car'):
            raise ValidationError('task does not have a car')
        if not json_task.get('driver'):
            raise ValidationError('task does not have a driver')
        car = Car.objects(id=ObjectId(json_task.get('car'))).first()
        if not car:
            raise ValidationError('input car not found')
        driver = Driver.objects(id=ObjectId(json_task.get('driver'))).first()
        if not driver:
            raise ValidationError('input driver not found')
        recorder = None
        if current_user.is_authenticated:
            recorder = current_user
        start_time = datetime.utcfromtimestamp(int(json_task.get('start_time')))
        task = Task(start_time=start_time,
                    car=car,
                    driver=driver,
                    recorder=recorder,
                    is_return=bool(json_task.get('is_return')))
        return task
        
    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py
        from random import choice

        cars = Car.objects()
        drivers = Driver.objects()
        users = User.objects()

        seed()
        for i in range(count):
            car = choice(cars)
            driver = choice(drivers)
            recorer = choice(users)
            start = forgery_py.date.date(True)
            if i % 5:
                task = Task(car=car,
                            driver=driver,
                            recorder=recorer,
                            start_time=start,
                            end_time=start+timedelta(days=3))
            else:
                task = Task(car=car,
                            driver=driver,
                            recorder=recorer,
                            start_time=start)
            task.save()

    @staticmethod
    def delete_all_tasks(condition=None):
        if not condition:
            return Task.objects().delete()

    @staticmethod
    def update_is_return():
        tasks = Task.objects()
        for task in tasks:
            if task.end_time:
                task.is_return = True
            else:
                task.is_return = False
            task.save()


def datetime_to_timestamp(time):
    if not time:
        return None
    if not isinstance(time, datetime):
        raise TypeError('Only accept datetime value.')
    return calendar.timegm(time.utctimetuple())