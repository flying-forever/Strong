import datetime

from flask import render_template, redirect, url_for, session, Blueprint

from strong.callbacks import login_required
from strong.utils import Time, TaskOrder
from strong.utils import flash_ as flash
from strong.forms import TaskForm, TaskSubmitForm
from strong.models import User, Task
from strong import db


# ------------------------------ 二、任务模块 ------------------------------ #


task_bp = Blueprint('task', __name__, static_folder='static', template_folder='templates')


@task_bp.context_processor
def make_template_context():
    """增加模板上下文变量"""
    return dict(TaskOrder=TaskOrder)


@task_bp.route('/')
@task_bp.route('/doing')
@login_required
def task_doing():
    tasks = Task.query.filter_by(uid=session['uid']).all()
    return render_template('task/task_doing.html', tasks=tasks, Time=Time)


# 代码丑陋，待重构
@task_bp.route('/done')
@task_bp.route('/done/<int:order_id>')
@login_required
def task_done(order_id: int=1):
    
    tasks = Task.query.filter_by(uid=session['uid'])
    TO = TaskOrder

    if order_id == TO.FINISH_DESC:
        tasks = tasks.order_by(Task.time_finish.desc())
    elif order_id == TO.FINISH_ASC:
        tasks = tasks.order_by(Task.time_finish.asc())
    elif order_id == TO.ADD_DESC:
        tasks = tasks.order_by(Task.time_add.desc())
    elif order_id == TO.ADD_ASC:
        tasks = tasks.order_by(Task.time_add.asc())
    elif order_id == TO.NAME_DESC:
        tasks = tasks.order_by(Task.name.desc())
    elif order_id == TO.NAME_ASC:
        tasks = tasks.order_by(Task.name.asc())

    
    tasks = tasks.all()
    return render_template('task/task_done.html', order_id=order_id, tasks=tasks, datetime=datetime, Time=Time)


@task_bp.route('/create', methods=['GET', 'POST'])
@login_required
def task_create():
    form = TaskForm()
    if form.validate_on_submit():
        # 重构：不想写这一行代码，能否默认从表单中提取所有参数，并传递给Task的构造函数？
        task = Task(name=form.name.data, exp=form.exp.data, need_minute=form.need_minute.data, uid=session['uid'])

        db.session.add(task)
        db.session.commit()

        flash('新任务添加成功！')
        return redirect(url_for('.task_doing'))
    return render_template('task/task_create.html', form=form)


@task_bp.route('/submit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_submit(task_id):
    form = TaskSubmitForm()
    task = Task.query.get(task_id)
    if form.validate_on_submit():

        # 完成任务增加经验（初次提交）
        if not task.is_finish:
            user = User.query.get(session['uid'])
            user.exp += task.exp
            db.session.commit()

        task.use_minute = Time(hours=form.use_hour.data, minutes=form.use_minute.data).get_minutes_all()
        task.describe = form.describe.data
        task.is_finish = True # 表示任务已经完成
        db.session.commit()

        flash('成功提交任务！')
        return redirect(url_for('.task_done'))
    
    # 表单回显 --> 修改已完成的任务时
    # 重构：能否在表单类中封装回显功能？
    form.describe.data = task.describe

    use_time = Time(minutes=task.use_minute)
    form.use_hour.data = use_time.hours
    form.use_minute.data = use_time.minutes
    return render_template('task/task_submit.html', form=form, task=task)


@task_bp.route('/delete/<int:task_id>')
@login_required
def task_delete(task_id):
    task = Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('成功删除任务！')
    return redirect(url_for('.task_doing'))


# ------------------------------ 三、胡乱尝试 ------------------------------ #
@task_bp.route('/test')
def test():
    """用于尝试一些新功能，或样式。"""
    return render_template('_test.html')
