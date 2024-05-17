from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
import math

from strong import db
from strong.models import Task, User
from strong.utils import Login, Clf
from strong.utils import flash_ as flash


data_bp = Blueprint('data', __name__, static_folder='static', template_folder='templates')


@data_bp.route('/')
def index():
    return redirect(url_for('.graph', **request.args))


def hour_per_day(year: int, month: int, tasks: list=None) -> list:
    '''统计某月每天的学习时间，单位(hour)'''
    # @tasks：避免重复的查询
    tasks: list[Task] = [task for task in tasks if task.time_finish.month == month and task.time_finish.year == year]
    h_pday = [0] * 32  # 每个月最多31天
    for task in tasks:
        h_pday[task.time_finish.day] += task.use_minute 
    # minute -> hour
    for i in range(32):
        h_pday[i] = round(h_pday[i] / 60, 2)  # 2:两位小数
    return h_pday


@data_bp.route('/get_data', methods=['GET', 'POST'])
def get_data():
    """月度统计与对比
    - 说明：折线堆叠图，本月和上月各一条线
    - types:
        - 0 : 折线堆叠图
        - 1 : 普通折线图，区域填充
    - 异步返回json"""
    # 备注：要不要把两个图表拆到不同函数呢？
    # 备注：这里用POST会有的奇怪，从函数功能上，GET更加符合

    # [choice] 月份选择 & 年份选择
    type = request.form.get('type', type=int)
    uid = request.form.get('uid', type=int, default=Login.current_id())
    # print('form:', request.form)

    now = datetime.utcnow()
    month = request.form.get('month', type=int, default=now.month)
    year = request.form.get('year', type=int, default=now.year)
    today = now.day if month == now.month else 31

    # 1 查询本月以及上月的数据
    tasks: list[Task] = (
        Task.query
        .filter_by(uid=uid, is_finish=True)
        .with_entities(Task.time_finish, Task.use_minute))

    if month == 1:  
        # 跨年
        l_year = year - 1 
        l_month = 12
    else:
        l_year = year
        l_month = month - 1

    # 1.1 统计每月学习的天数
    h_pday = hour_per_day(year=year, month=month, tasks=tasks)[:today+1]
    h_pday_l = hour_per_day(year=l_year, month=l_month, tasks=tasks)

    # 2 堆叠
    pday, pday_l = h_pday.copy(), h_pday_l.copy()
    for i in range(today):
        pday[i+1] = round(pday[i] + pday[i+1], 2)
    for i in range(len(pday_l) - 1):
        pday_l[i+1] = round(pday_l[i] + pday_l[i+1], 2)

    # 3 概览
    hours_all = max(pday)
    today_hour = round(pday[-1] - pday[-2], 2)
    average_hour = round(hours_all / today, 2)
    hours_all_l = pday_l[pday.index(hours_all)]
    x = [f'{i}日' for i in range(32)]

    # [choice] 使用堆叠吗
    if type == 0:
        pass
    elif type == 1:
        # 不使用堆叠版 - 回滚
        pday, pday_l = h_pday, h_pday_l

    datas = {'pday':pday, 'pday_l':pday_l, 'x':x, \
        'hours_all':hours_all, 'today_hour':today_hour, 'average_hour':average_hour, 'hours_all_l':hours_all_l, \
        'type':type, 'month':month, 'year':year}
    return jsonify(datas)


@data_bp.route('/<int:type>')
def data(type: int=0):
    '''月度数据页'''
    # 备注：这部分年月逻辑于get_data重复了
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    if not month or not year:
        now = datetime.utcnow()
        year, month = now.year, now.month
    print('页面', year, month)
    
    #[choice] 图表模板选择
    if type == 0:
        template = 'data/data.html'
    elif type == 1:
        template = 'data/data2.html'

    return render_template(template, type=type, month=month, year=year)
    

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
    gaps = [10**5, 7, 30, 90]
    tasks = [task for task in user.tasks if abs(task.time_finish - datetime.utcnow()) < timedelta(days=gaps[time_id])]
    
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


@data_bp.route('/tree_data')
@data_bp.route('/tree_data/<int:time_id>')
def get_tree_data(time_id=1):
    print('time_id', time_id)
    datas = tree_data(time_id)
    return jsonify(datas)


@data_bp.route('/graph')
def graph():
    '''学习时间的关系模板'''
    time_id = request.args.get('time_id', type=int, default=1)  # int | None； 要default，模板的下拉框用。
    
    datas = tree_data(time_id)
    return render_template('data/label.html', datas=datas, time_id=time_id, user=Login.current_user(), type=2)
