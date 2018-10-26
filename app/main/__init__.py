from flask import Blueprint

# 蓝本：参考《Flask Web开发》7.3.2章节
main = Blueprint('main', __name__)

from . import views