from flask import jsonify, Blueprint, current_app, request
from flask_cors import CORS
from strong import db
from strong.models import User, Task
from strong.utils import get_level
import time
from datetime import datetime


api_bp = Blueprint('api', __name__)
CORS(api_bp)


# -------------------------------- 一、尝试接口：task ------------------------------ #


user: User
@api_bp.before_request
def before_request():
    '''默认使用用户1'''
    global user
    user = User.query.get(1)


@api_bp.route('/hello')
def hello():
    r = {'name':user.name, 'level':get_level(exp=user.exp)}
    return jsonify(r)


def task_to_dict(task: Task):
    return {
        'id': task.id,
        'name': task.name,
        'use_minute': task.use_minute
    }


@api_bp.route('/task_done')
def task_done():
    ts = time.time()

    tasks: list[Task] = Task.query.filter(Task.uid==user.id, Task.is_finish==True).all()
    t_tasks = time.time()

    r = {'tasks': [task_to_dict(task) for task in tasks]}
    t_r = time.time()

    res = jsonify(r)
    t_js = time.time()

    print(f'[time] t_query={t_tasks-ts}, t_r={t_r-t_tasks}, t_js={t_js-t_r}')
    return res


@api_bp.route('/task_doing')
def task_doing():
    tasks: list[Task] = Task.query.filter_by(uid=user.id, is_finish=False).all()
    r = {'tasks': [task_to_dict(task) for task in tasks]}
    return jsonify(r)


@api_bp.route('/task_create', methods=['POST'])
def task_create():
    # 解析json数据, 获取name和exp，新建task
    data = request.json     ;print(f'[task create] {data}')
    task = Task(name=data['name'], exp=data['exp'], uid=user.id)
    db.session.add(task)
    db.session.commit()
    return jsonify(task_to_dict(task)), 201


@api_bp.route('/task_delete', methods=['POST'])
def task_delete():
    data = request.json
    task = Task.query.get(data['id'])       ;print(f'[task delete] {data},{task}')
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success':True})


@api_bp.route('/task_submit', methods=['POST'])
def task_submit():
    '''@data: {id, name, use_minute, describe}'''

    # 1 获取数据
    data = request.json  ;print(f'[task submit] {data}')
    task = Task.query.get(data['id'])
    # 2 备注：没有验证数据(wtf会有csrf问题)
    
    def data_commit(task):
        task.is_finish = True
        task.use_minute = data['use_minute']
        task.describe = data['describe']
        db.session.commit()
        return jsonify({'success':True})
    
    # 3 修改旧提交记录 -> 直接修改
    if task.is_finish:
        return data_commit(task)
    
    # 4-1 提交重复任务 -> 新拷贝
    if task.task_type == 1:
        task_new = Task(name=task.name, exp=task.exp, need_minute=task.need_minute, \
            uid=task.uid, task_type=task.task_type, bid=task.bid, tag_id=task.tag_id)
        db.session.add(task_new)

    # 4-2 增加经验
    user.exp += task.exp 
    task.is_finish = True
    task.time_finish = datetime.utcnow() # 记录初次提交的时间
    return data_commit(task)


