from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
# from flask_socketio import SocketIO
import pymysql
import os

from strong.config import config


# 应对服务器上的bug：_mysql is not defined
pymysql.install_as_MySQLdb()

# 创建数据库实例
db = SQLAlchemy()
migrate = Migrate()

# 其它扩展实例化
from flask_avatars import Avatars 
avatars = Avatars()  # 处理用户头像
# socketio = SocketIO()


def create_app(config_py=None):

    # 创建程序实例
    app = Flask('strong')
    config_name = os.getenv('FLASK_CONFIG', default='base')  # .flaskenv的环境
    print(f'[config] {config_name}')
    app.config.from_object(config[config_name])

    # 注册蓝图
    from strong.blueprints import auth_bp, task_bp, data_bp, book_bp, plan_bp, tag_bp #, try_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(task_bp, url_prefix='/task')
    app.register_blueprint(data_bp, url_prefix='/data')
    app.register_blueprint(book_bp, url_prefix='/book')
    app.register_blueprint(plan_bp, url_prefix='/plan')
    app.register_blueprint(tag_bp, url_prefix='/tag')
    # app.register_blueprint(try_bp, url_prefix='/try')

    # 注册api版本
    from strong.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # 要注册到app上的东西（而不是注册到蓝图）
    from strong.registers import register_index, register_context, register_getfile, register_move_site
    register_index(app)
    register_context(app)
    register_getfile(app)
    register_move_site(app)

    # 导入模型类，让数据库实例能找到它
    from strong import models

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    avatars.init_app(app)
    # socketio.init_app(app)

    return app
