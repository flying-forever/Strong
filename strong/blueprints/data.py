from flask import Blueprint, render_template, redirect, url_for, request
from datetime import datetime
import re, math, json

from strong import db
from strong.callbacks import login_required
from strong.models import Task, Book, User
from strong.utils import Login, Time, Clf
from strong.utils import flash_ as flash
from strong.forms import BookForm


data_bp = Blueprint('data', __name__, static_folder='static', template_folder='templates')


# ------------------------------ 一、功能函数 ------------------------------ #


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


# ------------------------------ 二、数据图表 ------------------------------ #


# 重构：要不要把两个图表拆到不同函数呢？
@data_bp.route('/')
@data_bp.route('/<int:type>')
@login_required
def data(type: int=0):
    """月度统计与对比
    - 说明：折线堆叠图，本月和上月各一条线
    - types:
        - 0 : 折线堆叠图
        - 1 : 普通折线图，区域填充"""

    # [choice] 月份选择 & 年份选择
    now = datetime.utcnow()
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if not year:
        year = now.year
    if not month:
        month = now.month 
    today = now.day if month == now.month else 31

    # 1 查询本月以及上月的数据
    tasks: list[Task] = (
        Task.query
        .filter_by(uid=Login.current_id(), is_finish=True)
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

    #[choice] 图表模板选择
    if type == 0:
        template = 'data/data.html'
    elif type == 1:
        template = 'data/data2.html'

    return render_template(
        template, pday=pday, pday_l=pday_l, x=x, 
        hours_all=hours_all, today_hour=today_hour, average_hour=average_hour, hours_all_l=hours_all_l,
        type=type, month=month, year=year)
    

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

    def set_parent(self, parent):
        self.parent = parent
        self.parent.children.append(self)
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

    def get_data(self):
        '''返回echarts需要的节点字典'''
        return {'id':self.id, 'name':self.name, 'value':round(self.value,2), 'symbolSize':math.sqrt(self.value)*5+1}
    def get_link(self):
        return {'id':next(self.link_id), 'source':str(self.id), 'target':str(self.pid)} if self.pid else None


@data_bp.route('/graph')
@login_required
def graph():
    '''学习时间的关系图'''
    # 这一版代码看着清晰多了，面向对象吗？
    
    user: User = Login.current_user()
    nodes: dict[int, Node] = {}  # id->node

    # 1 构建树，计算值
    # 1.1 创建节点
    for tag in user.tags:
        node = Node(id=tag.id, name=tag.name, pid=tag.pid)
        nodes[tag.id] = node

    # 合并同名任务
    d: dict[str, Node] = {}
    for t in user.tasks:
        if t.name not in d:
            d[t.name] = Node(id=t.id+Clf.idOffset, name=t.name, pid=t.tag_id, value=0)  # task是叶子节点，不会被pid索引的
        d[t.name].value += t.use_minute / 60  # m->h
    
    for node in d.values():
        nodes[node.id] = node

    # 1.2 连接节点，从每个根节点递归计算值
    for node in nodes.values():
        if node.pid:
            node.set_parent(nodes[node.pid])
    for node in nodes.values():
        if node.pid is None:
            node.forward()

    # 2 遍历树，返回点集和边集
    enodes, elinks = [], []
    for node in nodes.values():
        enodes.append(node.get_data())
        link = node.get_link()
        if link:
            elinks.append(link)

    datas = {'nodes':enodes, 'links':elinks}
    return render_template('data/label.html', datas=datas, user=user, type=2)
