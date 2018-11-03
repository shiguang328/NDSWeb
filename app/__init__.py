from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
# from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# from flask_pagedown import PageDown
from flask_mongoengine import MongoEngine
from pymongo import MongoClient
from config import config

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
# db = SQLAlchemy()
# pagedown = PageDown()
# client = MongoClient('mongodb://localhost')
# db = client.ndsweb
db = MongoEngine()

login_manager = LoginManager()

# By defalut, when a user attempts to access a @login_required view without being logged in,
# Flask-Login will flash a message and redirect them to the log in view.(If the login view
# is not set, it will abort with a 401 error.)
# Here is the setted login view.
login_manager.login_view = 'auth.login'

# set message flashed.(defalut is 'Please log in to access this page.')
login_manager.login_message = 'Please log in first.'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    # pagedown.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    return app