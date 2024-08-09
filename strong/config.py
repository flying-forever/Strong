from flask import current_app
import os


class BaseConfig(object):
    SECRET_KEY = 'qfmz'
    SQLALCHEMY_DATABASE_URI = os.getenv('sql_url_base')  # 从.flaskenv文件获取变量值，但你也可以直接写在这里
    UPLOAD_PATH = os.path.join(os.path.dirname(__file__), 'uploads')
    PORT = 3002
    HOST = f'http://127.0.0.1:{PORT}'  # 用于提供给jinja2模板


class RunConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv('sql_url_run')
    HOST = f'http://43.139.70.152:{BaseConfig.PORT}'


class DieConfig(RunConfig):
    NEW_SITE = 'http://43.139.70.152:3002/'
    

config = {
    'base': BaseConfig,
    'run': RunConfig,
    'die': DieConfig,
}
