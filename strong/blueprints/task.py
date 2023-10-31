import datetime

from flask import render_template, redirect, url_for, session, Blueprint, request

from strong.callbacks import login_required
from strong.utils import Time, TaskOrder, Login
from strong.utils import flash_ as flash
from strong.forms import TaskForm, TaskSubmitForm
from strong.models import User, Task
from strong import db
# 重构：在蓝本上统一注册装饰器

# ------------------------------ 二、任务模块 ------------------------------ #


task_bp = Blueprint('task', __name__, static_folder='static', template_folder='templates')


# 备注：还没写
@task_bp.before_request
@login_required
def login_protect():
    """为整个视图添加登录保护"""
    pass


@task_bp.context_processor
def make_template_context():
    """增加模板上下文变量"""
    return dict(TaskOrder=TaskOrder)


@task_bp.route('/')
@task_bp.route('/doing')
def task_doing():
    tasks = Task.query.filter_by(uid=Login.current_id()).order_by(Task.time_add.desc()).all() # 时间逆序
    return render_template('task/task_doing.html', tasks=tasks, Time=Time)


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

    return render_template('task/task_done.html', order_id=order_id, tasks=tasks, datetime=datetime, Time=Time)


@task_bp.route('/create', methods=['GET', 'POST'])
def task_create():
    form = TaskForm()
    if form.validate_on_submit():
        # 重构：不想写这一行代码，能否默认从表单中提取所有参数，并传递给Task的构造函数？
        task = Task(name=form.name.data, exp=form.exp.data, need_minute=form.need_minute.data, \
            uid=Login.current_id(), task_type=form.task_type.data)

        db.session.add(task)
        db.session.commit()

        flash('新任务添加成功！')
        return redirect(url_for('.task_doing'))
    return render_template('task/task_create.html', form=form)


@task_bp.route('/submit/<int:task_id>', methods=['GET', 'POST'])
def task_submit(task_id):
    """提交/修改任务的视图"""
    
    form = TaskSubmitForm()
    task = Task.query.get(task_id)
    if form.validate_on_submit():
        def form_commit(task):
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
                    uid=task.uid, task_type=task.task_type)
            db.session.add(task_new)
        # 3 提交任务（新） --> 增加经验
        user = Login.current_user()
        user.exp += task.exp
        return form_commit(task=task)

    # 表单回显 --> 修改已完成的任务时
    # 重构：能否在表单类中封装回显功能？
    use_time = Time(minutes=task.use_minute)
    form.use_hour.data = use_time.hours
    form.use_minute.data = use_time.minutes
    form.describe.data = task.describe
    
    return render_template('task/task_submit.html', form=form, task=task)


@task_bp.route('/delete/<int:task_id>')
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
