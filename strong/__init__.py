from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pymysql
import os

from strong.config import config


# 应对服务器上的bug：_mysql is not defined
pymysql.install_as_MySQLdb()

# 创建数据库实例
db = SQLAlchemy()
migrate = Migrate()

# 扩展实例化 - 处理用户头像
from flask_avatars import Avatars 
avatars = Avatars()


def create_app(config_py=None):

    # 创建程序实例
    app = Flask('strong')
    config_name = os.getenv('FLASK_CONFIG', default='run')  # .flaskenv的环境
    app.config.from_object(config[config_name])

    # 注册蓝图
    from strong.blueprints import auth_bp, task_bp, data_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(task_bp, url_prefix='/task')
    app.register_blueprint(data_bp, url_prefix='/data')

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

    return app
