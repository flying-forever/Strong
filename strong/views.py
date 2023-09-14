import datetime

from flask import render_template, flash, redirect, url_for, session

from strong.callbacks import login_required
from strong.utils import Time, TaskOrder
from strong.forms import TaskForm, TaskSubmitForm, LoginForm
from strong.models import User, Task
from strong import app, db


# ------------------------------ 一、用户模块 ------------------------------ #


@app.route('/')
@app.route('/home')
@login_required
def home():
    user = User.query.get(session['uid'])
    return render_template('home.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(name=form.username.data, password=form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            flash('注册成功！')
            return redirect(url_for('login'))
        except Exception as e:
            flash("该用户名已存在！请重新为自己构思一个独特的用户名吧！")
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # 验证用户名和密码以完成登录
        user = User.query.filter_by(name=form.username.data).first()
        if (user is not None) and (form.password.data == user.password):
            # 登录成功
            session['uid'] = user.id
            session['uname'] = user.name
            return redirect(url_for('home'))
        else:
            flash("用户名或密码错误！")
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """退出登录"""
    session['uid'] = None
    session['uname'] = None
    return redirect(url_for('login'))


# ------------------------------ 二、任务模块 ------------------------------ #


@app.route('/task')
@app.route('/task/doing/')
@login_required
def task_doing():
    tasks = Task.query.filter_by(uid=session['uid']).all()
    return render_template('task_doing.html', tasks=tasks)


# 代码丑陋，待重构
@app.route('/task/done')
@app.route('/task/done/<int:order_id>')
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
    return render_template('task_done.html', order_id=order_id, tasks=tasks, datetime=datetime, Time=Time)


@app.route('/task/create/', methods=['GET', 'POST'])
@login_required
def task_create():
    form = TaskForm()
    if form.validate_on_submit():

        task = Task(name=form.name.data, exp=form.exp.data, uid=session['uid'])

        db.session.add(task)
        db.session.commit()

        flash('新任务添加成功！')
        return redirect(url_for('task_doing'))
    return render_template('task_create.html', form=form)


@app.route('/task/submit/<int:task_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('task_done'))
    
    # 表单回显 --> 修改已完成的任务时
    # 重构：能否在表单类中封装回显功能？
    form.describe.data = task.describe

    use_time = Time(minutes=task.use_minute)
    form.use_hour.data = use_time.hours
    form.use_minute.data = use_time.minutes
    return render_template('task_submit.html', form=form, task=task)


@app.route('/task/delete/<int:task_id>')
@login_required
def task_delete(task_id):
    task = Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('成功删除任务！')
    return redirect(url_for('task_doing'))


# ------------------------------ 三、胡乱尝试 ------------------------------ #
@app.route('/test')
def test():
    """用于尝试一些新功能，或样式。"""
    return render_template('test.html')