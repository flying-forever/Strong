from flask import current_app
import os


class BaseConfig(object):
    SECRET_KEY = 'qfmz'
    SQLALCHEMY_DATABASE_URI = 'mysql://root:d30050305@localhost:3306/strong'
    UPLOAD_PATH = os.path.join(os.path.dirname(__file__), 'uploads')
    PORT = 3002
    HOST = f'http://127.0.0.1:{PORT}'


class RunConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'mysql://root:+Aa8848lf@127.0.0.1:3306/strong'
    HOST = f'http://43.139.70.152:{BaseConfig.PORT}'


class DieConfig(RunConfig):
    NEW_SITE = 'http://43.139.70.152:3002/'
    

config = {
    'base': BaseConfig,
    'run': RunConfig,
    'die': DieConfig,
}
