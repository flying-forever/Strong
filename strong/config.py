class BaseConfig(object):
    SECRET_KEY = 'qfmz'
    SQLALCHEMY_DATABASE_URI = 'mysql://root:d30050305@127.0.0.1:3306/strong'

class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'mysql://root:+Aa8848lf@127.0.0.1:3306/strong'
    
config = {
    'base': BaseConfig,
    'development': DevelopmentConfig,
}
