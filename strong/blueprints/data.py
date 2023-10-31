from flask import Blueprint, render_template
from datetime import datetime
from strong.callbacks import login_required
from strong.models import Task
from strong.utils import Login


data_bp = Blueprint('data', __name__, static_folder='static', template_folder='templates')


# 重构：代码职责宽泛，冗余高，算法效率低。
@data_bp.route('/')
@login_required
def data():
    """月度统计与对比
    - 说明：折线堆叠图，本月和上月各一条线"""

    # 1 查询本月以及上月的数据
    now = datetime.utcnow()
    tasks: list[Task] = (
        Task.query
        .filter_by(uid=Login.current_id(), is_finish=True)
        .with_entities(Task.time_finish, Task.use_minute))
    tasks_l = [task for task in tasks if task.time_finish.month == (now.month - 1)]
    tasks = [task for task in tasks if task.time_finish.month == now.month]

    # 2.1 统计本月每天的学习时间
    today = now.day
    pday = [0] * (today + 1)
    for task in tasks:
        pday[task.time_finish.day] += task.use_minute    
    for i in range(today):
        pday[i+1] += pday[i]

    # 2.2 统计上月每天的学习时间
    pday_l = [0] * 32
    for task in tasks_l:
        pday_l[task.time_finish.day] += task.use_minute    
    for i in range(len(pday_l) - 1):
        pday_l[i+1] += pday_l[i]

    # 3 分钟变小时，并保留两位小数
    for i in range(32):
        try:
            pday[i] = round(pday[i] / 60.0, 2)
            pday_l[i] = round(pday_l[i] / 60.0, 2)
        except Exception as e:
            pass

    # 4 概览
    hours_all = max(pday)
    average_hour = round(hours_all / today, 2)
    hours_all_l = pday_l[pday.index(hours_all)]
    x = [f'{i}日' for i in range(32)]

    return render_template(
        'data/data.html', pday=pday, pday_l=pday_l, x=x, 
        hours_all=hours_all, average_hour=average_hour, hours_all_l=hours_all_l)

