import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tongji university secret key'
    # MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.163.com')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '465'))
    MAIL_USE_SSL = True
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in \
        # ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # print(MAIL_USERNAME, MAIL_PASSWORD)

    FLASKY_MAIL_SUBJECT_PREFIX = '[NDSWeb]'
    FLASKY_MAIL_SENDER = 'NDSWeb Admin <13052353610@163.com>'
    FLASKY_ADMIN = os.environ.get('NDSWeb_ADMIN')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FLASKY_POSTS_PER_PAGE = 20
    FLASKY_FOLLOWERS_PER_PAGE = 50
    FLASKY_COMMENTS_PER_PAGE = 30

    MONGODB_SETTINGS = {
        'db': 'ndsdata',
        'host': 'localhost',
        'port': 27017
    }

    VEHICLE_TYPE = ('Car', 'Bus', 'SUV', 'Taxi', 'Truck', 'Motorcycle')
    POWER_TYPE = ('Gasoline', 'Electric', 'Hybrid')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite://'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}