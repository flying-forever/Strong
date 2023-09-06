from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pymysql


# 应对服务器上的bug：_mysql is not defined
pymysql.install_as_MySQLdb()

# 创建数据库实例
db = SQLAlchemy()
migrate = Migrate()

# 创建Flask程序实例
app = Flask('strong')

# 实例参数配置
app.config.from_pyfile('config.py')

# 数据库延后注册
db.init_app(app)
migrate.init_app(app, db)

# 导入数据模型，供视图函数使用
from strong import views
