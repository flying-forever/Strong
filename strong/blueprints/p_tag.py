from datetime import datetime, timedelta
import math

from flask import Blueprint, render_template, request, jsonify

from strong.set import Clf
from strong.utils import Login
from strong.utils import flash_ as flash
from strong.models import Task, Tag, User
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


def task_update(task_id, task_name, pid, uid, **kwargs):
    '''pid: int | None  (服务器python太老，不支持这样注解)'''
    print('task_name:', task_name, 'pid:', pid)
    tname_old = Task.query.filter(Task.id==task_id).first().name
    tasks = Task.query.filter(Task.name==tname_old, Task.uid==uid).all()

    # 修改任务名 - 所有同名记录（备注：未判断合并冲突，而且独立出来是不是更好？）
    if tname_old != task_name:
        print(f'[change task name]...{tname_old}->{task_name}')
        for t in tasks:
            t.name = task_name
            
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
    ops = [tag_create, tag_update, task_update]
    messages = ['创建出错，标签名不能重复', '标签更新出错', '任务绑定出错']
    if '' == node_id:
        op = 0
    elif int(node_id) < Clf.idOffset:
        op = 1
    else:
        op = 2
    res = {}
    res['success'] = ops[op](uid=uid, tag_id=node_id, pid=pid, tag_name=name, task_name=name, task_id=int(node_id)-Clf.idOffset)
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


class Node:
    def num_generator(n=123456789):
        for i in range(n):
            yield i 
    link_id = num_generator()

    def __init__(self, id, name, value=None, parent=None, pid=None) -> None:
        self.id = id
        self.name = name
        self.value = value  # hour
        self.parent = parent 
        self.children = []

        self.pid: int|None = pid  # 辅助属性
    def __repr__(self) -> str:
        return f'<Node id={self.id} name={self.name}, pid={self.pid}>'

    def is_task(self):
        return self.id >= Clf.idOffset
    def set_parent(self, parent):
        self.parent = parent
        self.parent.children.append(self)
        self.pid = self.parent.id  # 保持判断一致
    def compute(self):
        if self.value is None:
            self.value = 0
        for child in self.children:
            self.value += child.value
    def forward(self):
        for child in self.children:
            if child.value is None:
                child.forward()
        self.compute()

    def tree2dict(self):
        '''将整颗树返回为一个字典, return -> node_dict'''
        # Node.children == [] 时递归回升
        node_dict = {'id':self.id, 'name':self.name, 'value':round(self.value,2), 'symbolSize':math.sqrt(self.value)*5+1, 'children':[]}
        for child in self.children:
            child: Node
            node_dict['children'].append(child.tree2dict())
        return node_dict


def tree_data(time_id=1):
    '''返回标签系统的树结构数据
    - time_id: 0至今 1近一周 2近一月, 3近一季'''
    if time_id is None: time_id = 1

    # [choice 时间选择]
    user: User = Login.current_user()
    gaps = [10**5, 1, 7, 30, 90]
    _f = lambda t : abs(t.time_finish_local().date() - (datetime.utcnow() + timedelta(hours=8)).date()) < timedelta(days=gaps[time_id])
    tasks = [t for t in user.tasks if _f(t)]

    nodes: dict[int, Node] = {}  # id->node

    # 1 构建树，计算值
    # 1.1 创建节点
    for tag in user.tags:
        node = Node(id=tag.id, name=tag.name, pid=tag.pid)
        nodes[tag.id] = node

    # 1.2 合并同名任务
    d: dict[str, Node] = {}
    for t in tasks:
        if t.name not in d:
            d[t.name] = Node(id=t.id+Clf.idOffset, name=t.name, pid=t.tag_id, value=0)  # task是叶子节点，不会被pid索引的
        d[t.name].value += t.use_minute / 60  # m->h
    
    for node in d.values():
        nodes[node.id] = node

    # 1.3 连接节点，从每个根节点递归计算值; 没有标签的任务连接到other
    other = Node(id=-1, name='other', pid=None)
    nodes[other.id] = other
    for node in nodes.values():
        if node.pid:
            node.set_parent(nodes[node.pid])
        elif node.is_task():
            node.set_parent(other)

    # 1.3 没有父节点的顶级标签，连接到root
    root = Node(id=0, name=user.name, value=0, pid=None)
    for node in nodes.values():
        if node.pid is None:
            node.set_parent(root)
    root.forward()
    datas = root.tree2dict()
    datas['symbolSize'] = 5

    return datas


@tag_bp.route('/tree_data')
@tag_bp.route('/tree_data/<int:time_id>')
def get_tree_data(time_id=1):
    print('time_id', time_id)
    datas = tree_data(time_id)
    return jsonify(datas)


@tag_bp.route('/graph')
def graph():
    '''学习时间的关系模板'''
    time_id = request.args.get('time_id', type=int, default=1)  # int | None； 要default，模板的下拉框用。
    
    datas = tree_data(time_id)
    return render_template('plugin/tag_charts.html', datas=datas, time_id=time_id, user=Login.current_user(), type=2)
