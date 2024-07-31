from flask.views import MethodView
from flask import g, jsonify, Blueprint, current_app, make_response, redirect, request, url_for
from flask_cors import CORS

from strong import db
from strong.api.auth import generate_token, auth_required
from strong.api.errors import api_abort
from strong.models import User, Task
from strong.utils import get_level, Login

import time
from datetime import datetime


api_bp = Blueprint('api', __name__)
CORS(api_bp)


# -------------------------------- API、使用类组织资源 ------------------------------ #


class AuthTokenAPI(MethodView):

    def post(self):
        grant_type = request.form.get('grant_type')
        username = request.form.get('username')
        password = request.form.get('password')

        if grant_type is None or grant_type.lower() != 'password':
            return api_abort(code=400, message='The grant type must be password.')

        user: User = User.query.filter_by(name=username).first()
        if user is None or not user.validate_password(password):
            print(f'[error] {username} {password}')
            return api_abort(code=400, message='Either the username or password was invalid.')

        token = generate_token(user.id)

        response = jsonify({
            'access_token': token,
            'token_type': 'Bearer',
        })
        response.headers['Cache-Control'] = 'no-store'  # 告诉浏览器和代理服务器不要存储副本
        response.headers['Pragma'] = 'no-cache'
        return response


class UserAPI(MethodView):

    decorators = [auth_required]

    def get(self):
        user = g.current_user
        r = {'name': user.name, 'level': get_level(exp=user.exp)}
        return jsonify(r)


api_bp.add_url_rule('/oauth/token', view_func=AuthTokenAPI.as_view('token'), methods=['POST'])  # as_view设置端点值
api_bp.add_url_rule('/user', view_func=UserAPI.as_view('user'), methods=['GET'])


# -------------------------------- 老的 ------------------------------ #


@api_bp.route('/hello')
def hello():
    r = {'name':'名字', 'level':'等级'}
    return jsonify(r)
