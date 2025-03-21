from flask.views import MethodView
from flask import g, jsonify, Blueprint, current_app, make_response, redirect, request, url_for
from flask_cors import CORS

from strong import db
from strong.api.auth import generate_token, auth_required
from strong.api.errors import api_abort
from strong.models import User, Task
from strong.utils import get_level, Login, task_to_dict, get_dossier, recently_tasks

import time
from datetime import datetime


api_bp = Blueprint('api', __name__)
CORS(api_bp)


# -------------------------------- API、Task——待做和已完成 ------------------------------ #


def dossier():
    '''获取当天的已完成任务档案'''
    uid = g.current_user.id
    dossiers = get_dossier(tasks=recently_tasks(days=1, uid=uid))
    return jsonify(dossiers)


class FinishAPI(MethodView):
    
    decorators = [auth_required]

    def post(self):
        user = g.current_user
        id = request.form.get('id')
        minute = request.form.get('minute')
        describe = request.form.get('describe')
        task = Task.query.get(id)

        try:
            # 改用新建提交（以前是提交旧的，创建新的待做）
            user.exp += task.exp # 注：准备抛弃经验机制了
            task.time_add = datetime.utcnow()
            task_new = Task(name=task.name, is_finish=True, use_minute=minute, describe=describe, \
                            uid=user.id, bid=task.bid, tag_id=task.tag_id, plan_id=task.plan_id) # 保持外键联系
            db.session.add(task_new)
            db.session.commit()
            return jsonify(task_to_dict(task_new))
        except Exception as e:
            # 不try报错可能把很多本地代码都返回过去
            return api_abort(500, message=str(e))
        

class ToDoAPI(MethodView):

    # 之前Login类以session实现，我可以把g也加进去？
    decorators = [auth_required]

    def get(self):
        try:
            tasks: list[Task] = Task.query.filter_by(uid=g.current_user.id, is_finish=False).order_by(Task.time_add.desc()).all() # 时间逆序
            tasks = [task_to_dict(t) for t in tasks]
            return jsonify(tasks)
        except Exception as e:
            return api_abort(500, message=str(e))



def register_class(name, api_class: MethodView):
    api_bp.add_url_rule(f'/{name}', view_func=api_class.as_view(f'{name}')) # url; 端点名


def register_func(rule, func, auth_protect=True, methods=['GET']):
   if auth_protect:
       func = auth_required(func)
   api_bp.add_url_rule(rule, view_func=func, methods=methods)


register_class('todo', ToDoAPI)
register_class('finish', FinishAPI)
register_func('/dossier/today', func=dossier)


# -------------------------------- API、使用类组织资源——用户 ------------------------------ #


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
