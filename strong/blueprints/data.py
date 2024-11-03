from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
import math

from strong import db
from strong.models import Task, User
from strong.utils import Login
from strong.utils import flash_ as flash
from strong.set import Clf


data_bp = Blueprint('data', __name__, static_folder='static', template_folder='templates')


@data_bp.route('/')
def index():
    return redirect(url_for('.day_detail', type=2, **request.args))


def hour_per_day(year: int, month: int, tasks: list[Task]=None) -> list:
    '''统计某月每天的学习时间，单位(hour)'''
    # @tasks：避免重复的查询
    tasks: list[Task] = [task for task in tasks if task.tfc.month == month and task.tfc.year == year]
    h_pday = [0] * 32  # 每个月最多31天
    for task in tasks:
        h_pday[task.tfc.day] += task.use_minute 
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
    # 保留类方法，就不能.with_entities选列了。
    tasks = Task.query.filter_by(uid=uid, is_finish=True)

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
    

# 备注：感觉这个type传来传去
@data_bp.route('/day_detail/<int:type>')
def day_detail(type: int=2):
    '''日时间使用情况'''
    # 一周的任务列表
    user = Login.current_user()
    tasks = [t for t in user.tasks 
        if t.is_finish 
        and abs(t.time_finish - datetime.utcnow()) < timedelta(days=7)]  # 0~6
    print('len', len(tasks))
    types = list({t.name:t.name for t in tasks}.values())  # 去重任务名列表

    # 时间记录生成(index, name, end_time, duration:h)
    # - 备注：时区问题重构一下？
    now = datetime.utcnow() + timedelta(hours=8)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)  # 当天的23:59:59
    datas = [{
        'index':abs(t.time_finish + timedelta(hours=8) - today_end).days,  # 0~6
        'name':t.name,
        'end_time':round( (t.time_finish + timedelta(hours=8)).hour + t.time_finish.minute / 60, 2), 
        'duration':round(t.use_minute / 60, 2)} for t in tasks]
    
    return render_template('data/day_detail.html', type=type, types=types, datas=datas)
