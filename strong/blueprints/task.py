import datetime, re, os
from dataclasses import dataclass

from flask import render_template, redirect, url_for, session, Blueprint, request, current_app, jsonify

from strong.utils import Time, TaskOrder, Login, task_to_dict, random_filename, save_file, get_dossier
from strong.utils import flash_ as flash
from strong.forms import TaskForm, TaskSubmitForm, BookForm, UploadForm, PlanForm
from strong.models import User, Task, Plan
from strong.blueprints.p_plan import get_plans
from strong import db
# 重构：在蓝本上统一注册装饰器

# ------------------------------ 一、基础模块 ------------------------------ #


task_bp = Blueprint('task', __name__, static_folder='static', template_folder='templates')


@task_bp.context_processor
def make_template_context():
    """增加模板上下文变量"""
    return dict(TaskOrder=TaskOrder)


# ------------------------------ 二、任务模块 ------------------------------ #


@task_bp.route('/')
@task_bp.route('/doing')
def task_doing():
    tasks: list[Task] = Task.query.filter_by(uid=Login.current_id()).order_by(Task.time_add.desc()).all() # 时间逆序
    tasks = [task for task in tasks if not task.is_finish and task.plan_id is None] # 待完成的任务列表，无所属计划的

    plans = get_plans()['plans_doing']
    return render_template('task/task_doing.html', tasks=tasks, Time=Time, plans=plans)


@task_bp.route('/done')
@task_bp.route('/done/<int:order_id>')
def task_done(order_id: int=1):
    tasks = Task.query.filter_by(uid=Login.current_id())
    # 1 搜索
    keyword = request.args.get('keyword')
    tasks = tasks.filter(Task.name.like('%{}%'.format(keyword))) if keyword else tasks
    # 2 排序
    TO = TaskOrder
    order_way = {
        TO.FD: Task.time_finish.desc(),
        TO.FA: Task.time_finish.asc(),
        TO.AD: Task.time_add.desc(),
        TO.AA: Task.time_add.asc(),
        TO.ND: Task.name.desc(),
        TO.NA: Task.name.asc(),
    }
    tasks = tasks.order_by(order_way[order_id]).all()
    tasks = [task_to_dict(t) for t in tasks]

    return render_template('task/task_done.html', order_id=order_id, tasks=tasks, datetime=datetime, Time=Time)


@task_bp.route('/create', methods=['GET', 'POST'])
def task_create():
    form = TaskForm()
    if form.validate_on_submit():
        # 重构：不想写这一行代码，能否默认从表单中提取所有参数，并传递给Task的构造函数？
        task = Task(name=form.name.data.strip(), exp=form.exp.data, need_minute=form.need_minute.data, \
            uid=Login.current_id(), task_type=form.task_type.data)

        db.session.add(task)
        db.session.commit()

        flash('新任务添加成功！')
        return redirect(url_for('.task_doing'))
    # 备注：让用户自己设置可能更好
    form.exp.data = 1
    form.need_minute.data = 40
    return render_template('task/task_create.html', form=form)


@task_bp.route('/create_ajax', methods=['POST'])
def task_create_ajax():
    data = request.json
    
    name = data['name']
    need_minute = data['need_minute']
    plan_id = data['plan_id']
    task = Task(name=name, exp=1, need_minute=need_minute, task_type=1, uid=Login.current_id(), plan_id=plan_id)

    db.session.add(task)
    db.session.commit()
    return jsonify(task_to_dict(task))


@task_bp.route('/submit/<int:task_id>', methods=['GET', 'POST'])
@task_bp.route('/submit/<int:task_id>/<int:minute>', methods=['GET', 'POST'])
def task_submit(task_id, minute=None):
    """提交/修改任务的视图"""
    # 备注：构造url必须提供next查询字符串参数，见task_submit.html
    
    form = TaskSubmitForm()
    task = Task.query.get(task_id)
    if form.validate_on_submit():
        def form_commit(task: Task):
            """写入表单数据到数据库"""
            task.use_minute = Time(hours=form.use_hour.data, minutes=form.use_minute.data).get_minutes_all()
            task.describe = form.describe.data
            task.is_finish = True # 表示任务已经完成
            db.session.commit()
            flash('提交成功！')
            return redirect(url_for('.task_done'))
        # 1 修改旧任务 --> 写入表单数据
        if task.is_finish:
            return form_commit(task=task)
        # 2 提交重复任务（新） --> 创建一个新的拷贝
        if task.task_type == 1:
            task_new = Task(name=task.name, exp=task.exp, need_minute=task.need_minute, \
                    uid=task.uid, task_type=task.task_type, bid=task.bid, tag_id=task.tag_id)
            # 继承未截止的计划
            plan = Plan.query.get(task.plan_id)  # 备注：与plan模块的耦合
            if plan and not plan.is_end:
                task_new.plan_id = plan.id
            db.session.add(task_new)
        # 3 提交任务（新） --> 增加经验
        user = Login.current_user()
        user.exp += task.exp
        task.time_finish = datetime.datetime.utcnow() # 记录初次提交的时间
        return form_commit(task=task)

    # 表单回显 --> 修改已完成的任务时
    # 重构：能否在表单类中封装回显功能？
    use_time = Time(minutes=task.use_minute)
    form.use_hour.data = use_time.hours
    form.use_minute.data = use_time.minutes
    if task.describe:  # form类提供了“无”的默认值
        form.describe.data = task.describe
    # 从task.clock来，填入计时
    if minute:
        form.use_hour.data = minute // 60
        form.use_minute.data = minute % 60
    
    # “取消”按钮跳回上一个页面
    next_url = url_for(request.args.get('next'), task_id=task_id, **(request.args))
    return render_template('task/task_submit.html', form=form, task=task, next_url=next_url)


@task_bp.route('/delete/<int:task_id>')
def task_delete(task_id):
    task = Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('成功删除任务！')
    return redirect(request.referrer)


@task_bp.route('/clock/<int:task_id>')
@task_bp.route('/clock/<int:task_id>/<int:seconds_pass>')
def task_clock(task_id, seconds_pass=0):
    task = Task.query.get(task_id)
    minute = task.need_minute
    return render_template('task/clock.html', task=task, minute=minute, seconds_pass=seconds_pass)


@task_bp.route('/dossier')
def task_dossier():
    """已完成任务档案"""
    tasks = Task.query.filter_by(uid=Login.current_id(), is_finish=True).order_by(Task.time_finish.desc()).all()  # 档案列表也将是时间逆序的
    dses = get_dossier(tasks=tasks)
    return render_template('task/task_dossier.html', dossier=dses)


@task_bp.route('/record/<string:task_name>')
def task_record(task_name):
    '''@异步请求，对应任务名的完成记录'''
    tasks = Task.query.filter_by(uid=Login.current_id(), name=task_name, is_finish=True).order_by(Task.time_finish.desc()).all()
    tasks = [task_to_dict(t) for t in tasks]
    return jsonify(tasks)


@task_bp.route('/restart/<string:task_name>')
def task_restart(task_name):
    
    '''老任务重新创建为待做'''
    t = Task.query.filter_by(uid=Login.current_id(), name=task_name, is_finish=True).order_by(Task.time_finish.desc()).first()
    # 备注：代码较冗余，每个参数名要写两遍。
    # 没有继承plan_id，既重启任务不属于任何计划。
    task_new = Task(name=t.name, exp=t.exp, need_minute=t.need_minute, \
                    task_type=t.task_type, uid=t.uid, bid=t.bid, tag_id=t.tag_id)
    db.session.add(task_new)
    db.session.commit()
    flash('重启成功。')
    return redirect(url_for('.task_doing'))


# ------------------------------ 六、胡乱尝试 ------------------------------ #


@task_bp.route('/test')
def test():
    """用于尝试一些新功能，或样式。"""
    return render_template('data/data3.html')
