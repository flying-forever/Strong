from flask import Flask, render_template, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from functools import wraps

from forms import TaskForm, TaskSubmitForm, LoginForm


# 应对服务器上的bug：_mysql is not defined
import pymysql
pymysql.install_as_MySQLdb()


# ------------------------------ 一、配置实例 ------------------------------ #


# 创建数据库实例
db = SQLAlchemy()
migrate = Migrate()

# 创建Flask程序实例
app = Flask(__name__)

# 实例参数配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:d30050305@127.0.0.1:3306/strong'
app.config['SECRET_KEY'] = 'qfmz'

# 数据库延后注册
db.init_app(app)
migrate.init_app(app, db)

# 导入数据模型，供视图函数使用
from models import Task, User


# ------------------------------ 二、功能函数 ------------------------------ #


@app.before_first_request
def first():
    """初始化session，防止出现KeyError。"""
    session['uid'] = None
    session['uname'] = None


# 装饰器：要求视图函数登录才能访问
def login_required(func):
    """装饰器：要求视图函数登录才能访问"""

    @wraps(func)
    def decorated(*args, **kwargs):
        print('this is decorated')
        if session['uid'] is None:
            flash('请先登录！')
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return decorated


# ------------------------------ 三、用户模块 ------------------------------ #


@app.route('/')
def index():
    """重复的，以应付该路由"""
    return redirect(url_for('home'))


@app.route('/home')
@login_required
def home():
    print('this is home')
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


# ------------------------------ 四、任务模块 ------------------------------ #


@app.route('/task')
def task():
    """重复的，但保留以兼容"""
    return redirect(url_for('task_doing'))


@app.route('/task/doing/')
@login_required
def task_doing():
    tasks = Task.query.all()
    return render_template('task_doing.html', tasks=tasks)


@app.route('/task/done/')
@login_required
def task_done():
    tasks = Task.query.all()
    return render_template('task_done.html', tasks=tasks)


@app.route('/task/create/', methods=['GET', 'POST'])
@login_required
def task_create():
    form = TaskForm()
    if form.validate_on_submit():

        task = Task(name=form.name.data, exp=form.exp.data)

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

        task.describe = form.describe.data
        task.is_finish = True # 表示任务已经完成
        db.session.commit()

        flash('成功提交任务！')
        return redirect(url_for('task_done'))
    form.describe.data = task.describe
    return render_template('task_submit.html', form=form, task=task)


@app.route('/task/delete/<int:task_id>')
@login_required
def task_delete(task_id):
    task = Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('成功删除任务！')
    return redirect(url_for('task_doing'))
