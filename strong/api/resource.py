from flask.views import MethodView
from flask import g, jsonify, Blueprint, current_app, make_response, redirect, request, url_for
from flask_cors import CORS

from strong import db
from strong.api.auth import generate_token, auth_required
from strong.api.errors import api_abort
from strong.models import User, Task

from strong.utils import get_level, Login, task_to_dict, get_dossier, recently_tasks

import time
from datetime import datetime, timedelta


api_bp = Blueprint('api', __name__)
CORS(api_bp)


# -------------------------------- API、Task——待做和已完成 ------------------------------ #
# API数据格式：现在是接受表单数据(request.form.get)，返回json数据(jsonify)

def focus_records(name: str):
    '''一条专注对应的所有记录，按时间逆序'''
    # [性能] 查询0.0109秒，处理0.00102秒，总计0.0119秒
    # t1 = time.time()
    uid = g.current_user.id
    tasks:list[Task] = Task.query.with_entities(Task.describe, Task.use_minute, Task.time_finish)\
        .filter_by(uid=uid, name=name, is_finish=True)\
        .order_by(Task.time_finish.desc())\
        .all()
    # t2 = time.time()
    
    all_minute = 0
    for task in tasks:
        all_minute += task.use_minute
    def item2dict(task: Task):
        tf = task.time_finish + timedelta(hours=8)
        return {'describe':task.describe, 'use_minute':task.use_minute, 'time_finish':tf.strftime(f'%Y-%m-%d %H:%M:%S')}
    records = [item2dict(task) for task in tasks]
    # t3 = time.time()
    # print(f'查询{t2-t1:.3}秒，处理{t3-t2:.3}秒，总计{t3-t1:.3}秒')
    return jsonify({'all_minute':all_minute, 'count':len(tasks), 'name':name, 'records':records})


def focus_item_count(name: str):
    '''一条专注的统计数据：总时长，总次数'''
    # [性能不错] 查询0.016秒，统计0.001秒，总计0.017秒
    # t1 = time.time()
    uid = g.current_user.id
    tasks:list[Task] = Task.query.with_entities(Task.use_minute).filter_by(uid=uid, name=name, is_finish=True).all()
    # t2 = time.time()

    all_minute = 0
    for task in tasks:
        all_minute += task.use_minute
    # t3 = time.time()
    # print(f'查询{t2-t1:.3}秒，统计{t3-t2:.3}秒，总计{t3-t1:.3}秒')
    return jsonify({'all_minute':all_minute, 'count':len(tasks), 'name':name})


def focus_days():
    '''用户到今天的专注总天数。'''
    '''
    【性能优化】
    [查询速度很慢]
    查询1.029秒
    统计0.1785秒 总计1.207秒
    [优化手段：1、with_entities, 2、Task.time_finiesh to Task.tfc]
    tfc  20230831183796.0 time_finish  2023-08-31 18:18:26
    查询0.433秒
    统计0.01891秒 总计0.4519秒（快时可总计0.15秒）

    - 不知道为啥tfc返回的是float。不过float让查询和处理都快起来了。
    - 所以是，查询本身没有很慢，但mysql与python对接很慢。
    '''
    # t1 = time.time()
    uid = g.current_user.id
    tasks:list[Task] = Task.query.with_entities(Task.tfc).filter_by(uid=uid, is_finish=True).all()
    # t2 = time.time()
    # print('tfc ', tasks[0].tfc, 'time_finish ')
    # print('tfc ', tasks[11].tfc, 'time_finish ')
    # print(f'查询{t2-t1:.4}秒')

    d = {}
    for task in tasks:
        # date: str = task.time_finish.strftime(f'%Y-%m-%d')
        date = int(task.tfc) // 1000_000
        d[date] = True
    # t3 = time.time()
    # print(f'统计{t3-t2:.4}秒 总计{t3-t1:.4}秒')
    return jsonify({'focus_days':len(d)})
    

def dossier_today():
    '''api：获取当天的已完成任务档案（合并同名）'''
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
            task.time_add = datetime.utcnow() # 方便把刚做过的专注排序到前面
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
    # uid = g.current # 随笔：怎么有个半截代码在这里

    def get(self):
        try:
            tasks: list[Task] = Task.query.filter_by(uid=g.current_user.id, is_finish=False).order_by(Task.time_add.desc()).all() # 时间逆序
            tasks = [task_to_dict(t) for t in tasks]
            return jsonify(tasks)
        except Exception as e:
            return api_abort(500, message=str(e))
        
    def post(self):
        # 从request获取name, minute, describe
        user = g.current_user
        name = request.form.get('name')
        minute = request.form.get('minute')
        describe = request.form.get('describe')

        try:
            task: Task = Task(name=name, need_minute=minute, describe=describe, uid=user.id, is_finish=False, task_type=1)
            db.session.add(task)
            db.session.commit()
            return jsonify(task_to_dict(task))
        except Exception as e:
            return api_abort(500, message=str(e))
    
    def delete(self):
        pass
        # uid = 
        

def register_class(name, api_class: MethodView):
    api_bp.add_url_rule(f'/{name}', view_func=api_class.as_view(f'{name}')) # url; 端点名


def register_func(rule, func, auth_protect=True, methods=['GET']):
   if auth_protect:
       func = auth_required(func)
   api_bp.add_url_rule(rule, view_func=func, methods=methods)


register_class('todo', ToDoAPI)
register_class('finish', FinishAPI)
register_func('/dossier/today', func=dossier_today) # 相比装饰器在函数头上，这样可以更集中看到所有路由。
register_func('/focus_days', func=focus_days)
register_func('/focus_item_count/<string:name>', func=focus_item_count)
register_func('/focus_records/<string:name>', func=focus_records)

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
