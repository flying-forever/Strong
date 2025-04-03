'''conftest.py对其所在目录及其子目录生效。'''

from flask.testing import FlaskClient
from flask import Flask
import pytest


class TestConfig(object):
    # 覆盖数据库配置
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True


@pytest.fixture(scope="module")
def app():
    from strong import create_app, db
    app = create_app(config_other=TestConfig)
    
    # 初始化数据库
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope="module")
def client(app) -> FlaskClient:
    return app.test_client()
