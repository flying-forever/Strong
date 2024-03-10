from flask import Blueprint, render_template, redirect, url_for, request
from datetime import datetime
import re

from strong import db
from strong.callbacks import login_required
from strong.models import Task, Book
from strong.utils import Login, Time
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


# 重构：代码职责宽泛，冗余高，算法效率低。
@data_bp.route('/')
@data_bp.route('/<int:type>')
@login_required
def data(type: int=0):
    """月度统计与对比
    - 说明：折线堆叠图，本月和上月各一条线
    - types:
        - 0 stack: 折线堆叠图
        - 1 line: 普通折线图"""

    # [choice] 月份选择
    now = datetime.utcnow()
    month = request.args.get('month', type=int)
    month = month if month else now.month
    today = now.day if month == now.month else 31

    # 1 查询本月以及上月的数据
    tasks: list[Task] = (
        Task.query
        .filter_by(uid=Login.current_id(), is_finish=True)
        .with_entities(Task.time_finish, Task.use_minute))

    if month == 1:  
        # 跨年
        l_year = now.year - 1 
        l_month = 12
    else:
        l_year = now.year
        l_month = month - 1

    # 1.1 统计每月学习的天数
    h_pday = hour_per_day(year=now.year, month=month, tasks=tasks)[:today+1]
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

    return render_template(
        'data/data.html', pday=pday, pday_l=pday_l, x=x, 
        hours_all=hours_all, today_hour=today_hour, average_hour=average_hour, hours_all_l=hours_all_l,
        type=type, month=month)
    