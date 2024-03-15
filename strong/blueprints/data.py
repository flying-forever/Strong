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
    

@data_bp.route('/graph')
@login_required
def graph():
    # 备注：先简单实现，利用数据库的反向引用
    # 备注：字段引用太多，且与前端样式耦合高
    # 记录：字段名字容易写错，如symbolSize -> SymbolSize
    # 备注：id冲突问题有待处理
    # 备注：尺寸适配问题待解决(归一化)
    # 备注：标签组织成了树形结构，值的计算得重写一下

    def num_generator(n=123456789):
        for i in range(n):
            yield i 
    link_id = num_generator()
    idOffset = Clf.idOffset  # task的id加上偏移，避免与tag的id冲突

    user: User = Login.current_user()
    nodes = []
    links = []
    
    # 查询标签生成结点
    allTime = 0
    for tag in user.tags:
        bTime = sum([t.use_minute for t in tag.tasks])
        allTime += bTime
        nodes.append({'id':tag.id, 'name':tag.name, 'value':bTime, 'symbolSize':1, 'label':{'show':True, 'fontSize':10}})
        # 和父标签的连接
        if tag.pid:
            links.append({'id':next(link_id), 'source':tag.id, 'target':tag.pid})

    # 合并同名任务，生成结点
    d = {}  # dict[name:node]
    for t in user.tasks:
        if t.name not in d:
            d[t.name] = {'id':t.id + idOffset, 'name':t.name, 'value':0, 'symbolSize':1}
            nodes.append(d[t.name])
            if t.tag_id:
                links.append({'id':next(link_id), 'source':t.id + idOffset, 'target':t.tag_id})
        d[t.name]['value'] += t.use_minute 
        
    # 将书籍链接到总结点
    # links += [{'id':next(link_id), 'source':b.id, 'target':0} for b in user.tags]
    # nodes.append({'id':0, 'name':user.name, 'value':allTime, 'symbolSize':1, 'label':{'show':True, 'fontSize':16}})

    # 整合数据 - 单位转换与格式适配
    for node in nodes:
        node['value'] = round(node['value'] / 60.0, 2)
        node['symbolSize'] = math.sqrt(node['value']) * 5 + 1
    for link in links:
        link['source'] = str(link['source'])  # echarts中字符串找id，整数找索引
        link['target'] = str(link['target'])
    datas = {'nodes':nodes, 'links':links}
    datas = json.dumps(datas)
    return render_template('data/label.html', datas=datas, user=user, type=2)
