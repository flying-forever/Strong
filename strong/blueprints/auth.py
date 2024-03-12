from flask import render_template, redirect, url_for, session, Blueprint, make_response, request, current_app
from flask import jsonify, send_from_directory

import os, json
from datetime import datetime

from strong.callbacks import login_required
from strong.utils import Login, get_level, get_exp, random_filename
from strong.utils import flash_ as flash
from strong.forms import LoginForm, UserForm, UploadForm, UpJsonForm
from strong.models import User, Book, Task
from strong import db


# ------------------------------ 一、用户模块 ------------------------------ #


auth_bp = Blueprint('auth', __name__, static_folder='static', template_folder='templates')


@auth_bp.before_request
def remenber_login():
    user_id: str = request.cookies.get('remenber_user') 

    # 若没有登录，则自动登录
    if user_id and Login.is_login(): 
        user = User.query.get(user_id)
        Login.login(user=user)
        print('已自动登录... ', user)


@auth_bp.route('/home')
@login_required
def home():
    user: User = Login.current_user()
    level = get_level(exp=user.exp)
    need_exp = get_exp(level + 1) - user.exp
    return render_template('auth/home.html', user=user, level=level, need_exp=need_exp)


@auth_bp.route('/modify', methods=['GET', 'POST'])
@login_required
def modify():
    """修改用户基本信息"""
    form = UserForm()
    user: User = User.query.get(Login.current_id())
    level = get_level(exp=user.exp)
    need_exp = get_exp(level + 1) - user.exp
    
    if form.validate_on_submit():
        user.name = form.username.data 
        user.introduce = form.introduce.data 
        user.email = form.email.data
        db.session.commit() 
        flash('修改成功！')
        return redirect(url_for('.home'))
    # 表单回显
    form.username.data = user.name 
    form.introduce.data = user.introduce
    form.email.data = user.email

    return render_template('auth/modify.html', form=form, user=user, level=level, need_exp=need_exp)


@auth_bp.route('/upload_avatar', methods=['GET', 'POST'])
@login_required
def upload_avatar():
    """上传自定义头像"""
    user: User = Login.current_user()
    form = UploadForm()
    if form.validate_on_submit():
        # 保存到文件系统
        f = form.photo.data 
        filename = random_filename(f.filename)
        f.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
        # 文件名(而非路径)写入数据库 - 文件所在路径将是可变的
        user.avatar = filename
        db.session.commit()
        flash('上传成功！')
        return redirect(url_for('.home'))
    return render_template('auth/upload.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = LoginForm()
    if form.validate_on_submit():
        user = User(name=form.username.data, password=form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            flash('注册成功！')
            return redirect(url_for('.login'))
        except Exception as e:
            flash("该用户名已存在！请重新为自己构思一个独特的用户名吧！", 'danger')
    return render_template('auth/register.html', form=form)


# 重构：已经登录则不重复登录
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # 验证用户名和密码以完成登录
        user = User.query.filter_by(name=form.username.data).first()
        if (user is not None) and (form.password.data == user.password):
            
            Login.login(user=user)
            
            # 使用cookie记住登录
            # 疑惑：实际保存的时间远大于我设置的20s，不知具体是多久。
            response = make_response(redirect(url_for('.home')))
            if form.remenber.data is True:
                response.set_cookie('remenber_user', str(user.id).encode('utf-8'), max_age=20)
                
            return response
        else:
            flash("用户名或密码错误！", 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    """退出登录"""
    Login.logout()

    # 并删除“记住登录”状态
    response = make_response(redirect(url_for('.login')))
    response.set_cookie('remenber_user', ''.encode('utf-8'), max_age=0)

    return response


@auth_bp.route('/export')
@login_required
def export_user():
    '''导出用户的书籍和任务数据，得到一个json文件
    - 注：不保存图片'''
    # 备注：附带一些元信息？如导出时间。

    def obj2json(objs: list, excludes: list):
        '''将对象列表变成json数据，并排除一些属性'''
        # 备注：可以补充说明一下json数据的内部结构
        ds = {}
        for obj in objs:
            one = obj.__dict__
            for k in excludes:
                one.pop(k)
            ds[obj.id] = one
        return ds

    user: User = Login.current_user()
    books: list[Book] = user.books
    tasks: list[Task] = user.tasks
    # 1 书籍
    excludes = ['_sa_instance_state', 'cover']
    d_books = obj2json(books, excludes)
    # 2 任务
    excludes = ['_sa_instance_state']
    d_tasks = obj2json(tasks, excludes)
    # 3 用户信息
    d_user = user.__dict__
    excludes = ['_sa_instance_state', 'password', 'avatar', 'time_add', 'books', 'tasks']
    for k in excludes:
        d_user.pop(k)

    # 4 返回数据文件
    data = {'books':d_books, 'tasks':d_tasks, 'user':d_user}
    data = jsonify(data)
    response = make_response(data)
    response.headers['Content-Disposition'] = 'attachment; filename=data.json'
    return response
    

@auth_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_user():
    '''用上传的json文件，“覆盖”用户数据'''
    # 备注：把一次导入作为原子操作，未全部成功时回滚？
    # 备注：这一段代码非常丑陋

    form = UpJsonForm()
    if form.validate_on_submit():
        f = form.file.data.read() 
        f = json.loads(f)
        uinfo, books, tasks = f['user'], f['books'], f['tasks']
        user: User = Login.current_user() 
        wait_dels = [b for b in user.books] + [t for t in user.tasks]

        try:
            # 1 创建书籍
            # 备注：能否已有的书籍就直接修改？
            for id in books:
                create_b = Book(uid=user.id)
                for k in books[id]:
                    if k not in ['id', 'uid', 'bid']:
                        create_b.__dict__[k] = books[id][k]
                books[id] = create_b  # 方便task绑定到新的bid
                db.session.add(create_b)
            # a = None
            # a[1] = 0
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print('[error] import_user...', e)
            flash('导入失败', 'danger')
            return redirect(url_for('.home'))

        try:
            # 2 创建任务并绑定书籍
            books: dict[str, Book]
            for task in tasks.values():
                # 2.1 创建
                create_t = Task(uid=user.id)
                for k in task:
                    if k not in ['id', 'uid', 'bid', 'time_add', 'time_finish']:
                        create_t.__dict__[k] = task[k]
                # 2.2 绑定书籍
                bid_old = task['bid']  # str(number) | None
                if bid_old:
                    create_t.bid = books[str(bid_old)].id
                # 2.3 从字符串解析时间对象
                time_add = datetime.strptime(task['time_add'], r'%a, %d %b %Y %H:%M:%S %Z')
                time_finish = datetime.strptime(task['time_finish'], r'%a, %d %b %Y %H:%M:%S %Z')
                create_t.time_add = time_add
                create_t.time_finish = time_finish

                db.session.add(create_t)

            # 3 写入用户信息
            user.name = uinfo['name']
            user.email = uinfo['email']
            user.exp = uinfo['exp']
            user.introduce = uinfo['introduce']
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print('[error] import_user...', e)
            flash('导入失败', 'danger')
            return redirect(url_for('.home'))

        # 4 删除旧数据
        for item in wait_dels:
            db.session.delete(item)
        db.session.commit()
        flash('数据导入成功')
        return redirect(url_for('.home'))
    return render_template('auth/upload.html', form=form)
