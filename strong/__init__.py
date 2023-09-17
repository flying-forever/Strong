from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pymysql


# 应对服务器上的bug：_mysql is not defined
pymysql.install_as_MySQLdb()

# 创建数据库实例
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_py=None):

    app = Flask('strong')
    app.config.from_pyfile('config.py')

    from strong.blueprints import auth_bp, task_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(task_bp, url_prefix='/task')

    register_index(app)

    from strong import models

    db.init_app(app)
    migrate.init_app(app, db)

    return app


def register_index(app):
    @app.route('/')
    def index():
        return redirect(url_for('auth.home'))
