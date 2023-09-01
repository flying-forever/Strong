from flask import Flask, render_template, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from forms import TaskForm, TaskSubmitForm


# 应对服务器上的bug：_mysql is not defined
import pymysql
pymysql.install_as_MySQLdb()

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

# 自动登录内置用户
@app.before_request
def login():
    """@注意：如果数据库里没有用户，则会报错"""
    user = User.query.first()
    session['uid'] = user.id
    session['uname'] = user.name
    print(f"已登录用户{user}")


@app.route('/')
def index():
    """重复的，以应付该路由"""
    return redirect(url_for('home'))


@app.route('/home')
def home():
    user = User.query.get(session['uid'])
    return render_template('home.html', user=user)


@app.route('/task')
def task():
    """重复的，但保留以兼容"""
    return redirect(url_for('task_doing'))


@app.route('/task/doing/')
def task_doing():
    tasks = Task.query.all()
    return render_template('task_doing.html', tasks=tasks)


@app.route('/task/done/')
def task_done():
    tasks = Task.query.all()
    return render_template('task_done.html', tasks=tasks)


@app.route('/task/create/', methods=['GET', 'POST'])
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
def task_delete(task_id):
    task = Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('成功删除任务！')
    return redirect(url_for('task_doing'))
