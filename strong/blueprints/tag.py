from flask import Blueprint, request, jsonify

from strong.callbacks import login_required
from strong.utils import Login, Clf
from strong.utils import flash_ as flash
from strong.models import Task, Tag
from strong import db


tag_bp = Blueprint('tag', __name__, static_folder='static', template_folder='templates')


def tag_create(tag_name, pid, uid, **kwargs):
    '''重名 -> False'''
    tag = Tag.query.filter(Tag.name==tag_name, Tag.uid==uid).first()
    if tag is not None: return False
    tag = Tag(name=tag_name, uid=uid, pid=pid)
    db.session.add(tag)
    db.session.commit()
    return True


def tag_update(tag_id, tag_name, pid, uid, **kwargs):
    # 备注：这样好像太灵活，比如传入一个找不到的pname，也会将父节点置空
    tag = Tag.query.filter(Tag.id==tag_id, Tag.uid==uid).first()
    tag.name = tag_name
    tag.pid = pid
    db.session.commit()
    return True


def task_bind_update(task_name, pid, uid, **kwargs):
    '''pid: int | None  (服务器python太老，不支持这样注解)'''
    print('task_name:', task_name, 'pid:', pid)
    tasks = Task.query.filter(Task.name==task_name, Task.uid==uid).all()
    # print('tasks,', tasks)
    for t in tasks:
        t.tag_id = pid
    db.session.commit()
    return True


@tag_bp.route('/tag/node', methods=['GET', 'POST'])
def tag_node():
    # 1 解析数据:str | '' | None
    print('form:', request.form)
    node_id = request.form.get('tagid')
    name = request.form.get('tagname').strip()
    pname = request.form.get('pname')

    uid = Login.current_id()
    pid = Tag.query.filter(Tag.name==pname, Tag.uid==uid).first().id if pname else None

    # 2 判断操作类型
    ops = [tag_create, tag_update, task_bind_update]
    messages = ['创建出错，标签名不能重复', '标签更新出错', '任务绑定出错']
    if '' == node_id:
        op = 0
    elif int(node_id) < Clf.idOffset:
        op = 1
    else:
        op = 2
    res = {}
    res['success'] = ops[op](uid=uid, tag_id=node_id, pid=pid, tag_name=name, task_name=name)
    res['message'] = messages[op] if not res['success'] else ''
    return jsonify(res)
    

@tag_bp.route('/tag/delete', methods=['GET', 'POST'])
def tag_delete():
    '''异步删除标签'''
    # 如果是task，id偏移很大，反正在数据库也查不到
    res = {'success':True, 'message':'...'}
    tagid = request.form.get('tagid')
    tag = Tag.query.filter(tagid==Tag.id, Login.current_id()==Tag.uid).first()
    if tag:
        db.session.delete(tag)
        db.session.commit()
    else:
        res['success'] = False
    return jsonify(res)

