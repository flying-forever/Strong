from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from wtforms import BooleanField
import pymysql


# 应对服务器上的bug：_mysql is not defined
pymysql.install_as_MySQLdb()

# 创建数据库实例
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_py=None):

    # 创建程序实例
    app = Flask('strong')
    app.config.from_pyfile('config.py')

    # 注册蓝图
    from strong.blueprints import auth_bp, task_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(task_bp, url_prefix='/task')

    # 要注册到app上的东西（而不是注册到蓝图）
    register_index(app)
    register_context(app)

    # 导入模型类，让数据库实例能找到它
    from strong import models

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)

    return app


def register_index(app):
    @app.route('/')
    def index():
        
        # 设置session的过期时间，默认为30天
        from flask import session
        session.permanent = True

        return redirect(url_for('auth.home'))


def register_context(app):
    @app.context_processor
    def make_template_context():
        """增加模板上下文变量"""
        return dict(BooleanField=BooleanField, isinstance=isinstance)
