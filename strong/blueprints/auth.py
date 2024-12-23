from flask import render_template, redirect, url_for, session, Blueprint, make_response, request, current_app
from flask import jsonify, send_from_directory

import os, json
import traceback  # 错误追踪
from datetime import datetime
from urllib.parse import quote

from strong.wraps import login_required
from strong.utils import Login, get_level, get_exp, random_filename, save_file
from strong.utils import flash_ as flash
from strong.forms import LoginForm, UserForm, UploadForm, UpJsonForm
from strong.models import Plan, User, Book, Task, Tag, Follow
from strong import db


auth_bp = Blueprint('auth', __name__, static_folder='static', template_folder='templates')


@auth_bp.before_request
def remenber_login():
    user_id: str = request.cookies.get('remenber_user') 

    # 若没有登录，则自动登录
    if user_id and Login.is_login(): 
        user = User.query.get(user_id)
        Login.login(user=user)
        print('已自动登录... ', user)


# ------------------------------ 一、用户登录 ------------------------------ #


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


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 重构：已经登录则不重复登录
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
                response.set_cookie('remenber_user', value=str(user.id), max_age=20)
                
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
    response.set_cookie('remenber_user', value='', max_age=0)

    return response


# ------------------------------ 二、个人信息 ------------------------------ #


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
        user.avatar = save_file(form.photo.data)
        db.session.commit()
        flash('上传成功！')
        return redirect(url_for('.home'))
    return render_template('auth/upload.html', form=form)


@auth_bp.route('/export')
@login_required
def export_user():
    '''导出用户的书籍和任务数据，得到一个json文件
    - 注：不保存图片；也不包括好友关系，仅个人数据。'''
    # 备注：哪些字段需要导出，哪些字段导入需要用到，可以捋一下。

    def obj2dict(objs: list, excludes: list):
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
    books: list[Book] = user.books  # <class 'sqlalchemy.orm.collections.InstrumentedList'>, 其实不是list
    tasks: list[Task] = user.tasks
    tags: list[Tag] = user.tags
    plans: list[Plan] = user.plans
    excludes_b = ['_sa_instance_state', 'cover']
    excludes_t = ['_sa_instance_state']
    excludes_u = ['_sa_instance_state', 'password', 'avatar', 'time_add', 'books', 'tasks', 'tags', 'plans']  # 备注：为啥user类需要排除关系属性？
    excludes_tag = ['_sa_instance_state']
    excludes_plans = ['_sa_instance_state', 'cover']
    
    d_books = obj2dict(books, excludes_b)  # {id:int -> 对象字典}
    d_tasks = obj2dict(tasks, excludes_t)
    d_tags = obj2dict(tags, excludes_tag)
    d_plans = obj2dict(plans, excludes_plans)
    d_user = user.__dict__
    for k in excludes_u:
        d_user.pop(k)

    # 返回数据文件
    # books|tasks：dict[id:str, 对象字典], user: 对象字典
    data = {'books':d_books, 'tasks':d_tasks, 'user':d_user, 'tags':d_tags, 'plans':d_plans}
    data = jsonify(data)
    tm = datetime.now().strftime(r"%Y-%m-%d")  # 文件被导出的时间

    response = make_response(data)
    response.headers['Content-Disposition'] = f'attachment; filename={quote(user.name)}{tm}.json'  # quote:编码中文
    return response


@auth_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_user():
    '''用上传的json文件，“覆盖”用户数据'''
    # 备注：总是碰到id问题，原来的外键pid已经失效。而新建的标签，不commit就不能从数据库获得id
    # 但其实可以手动指定id，以及相应外键
    # 备注：运行较慢
    # 备注：要加一个表（比如计划），要改动的地方还是太多了

    def strptime(time: datetime):
        '''我解析json导出的datetime时间用'''
        return  datetime.strptime(time, r'%a, %d %b %Y %H:%M:%S %Z')

    def create_book(books):
        '''@books元素：类json字典 -> Book对象, 为了获得新的id'''
        # 备注：能否已有的书籍就直接修改？
        for id in books:
            create_b = Book(uid=Login.current_id())
            for k in books[id]:
                if k not in ['id', 'uid', 'bid']:  # 备注：这里为啥要写'bid'？
                    create_b.__dict__[k] = books[id][k]
            books[id] = create_b  # 方便task绑定到新的bid
            db.session.add(create_b)

    def create_tag(tags):
        '''创建标签记录，树形结构
        - 更新tag的'id'字段'''

        # 0 查询标签表中最新的ID
        def id_generator():
            '''为了手动指定新建tag的id'''
            try:
                latest_id = Tag.query.order_by(Tag.id.desc()).first().id  + 1
            except:
                latest_id = 1
            for i in range(latest_id + 1, latest_id + 12345678):
                yield i
        get_id = id_generator()

        # 1 创建tags，此时的pid是旧的
        # tags -> {ida -> {idb, pid}}，先将idb修改为新的，pid与ida仍然是对应的
        for ida in tags:
            tags[ida]['id'] = next(get_id)
        
        # 2 创建新的tags实例
        for ida in tags:
            tag = tags[ida]
            create = Tag(id=tag['id'], uid=Login.current_id(), name=tag['name'])
            tag['create'] = create
            db.session.add(create)
        db.session.commit()

        # 3 写入外键，这需要在commit之后，否则外键约束报错
        for ida in tags:
            tag = tags[ida]
            if tag['pid']:
                tag['create'].pid = tags[str(tag['pid'])]['id']

    def create_plan(plans):
        '''字典 -> 新建Plan对象，与book类似'''
        for id in plans:
            create_p = Plan(uid=Login.current_id())
            for k in plans[id]:
                if k not in ['id', 'uid', 'start_time', 'end_time']:
                    create_p.__dict__[k] = plans[id][k]
            start_time = strptime(plans[id]['start_time'])
            end_time = strptime(plans[id]['end_time']) if plans[id]['end_time'] else None
            create_p.start_time = start_time
            create_p.end_time = end_time
            plans[id] = create_p  # 方便task绑定到新的plan_id
            db.session.add(create_p)

    def create_task(tasks, books, tags, plans):
        '''创建任务记录，同时绑定书籍，和标签'''
        books: dict[str, Book]
        for task in tasks.values():
            # 2.1 创建
            create_t = Task(uid=Login.current_id())
            for k in task:
                if k not in ['id', 'uid', 'bid', 'time_add', 'time_finish']:  # 备注：暂未导出plan数据
                    create_t.__dict__[k] = task[k]

            # 2.2 绑定书籍
            bid_old = task['bid']  # int | None
            if bid_old:
                create_t.bid = books[str(bid_old)].id  # json的索引是str

            # 2.3 绑定标签
            tag_id_old = task['tag_id']
            if tag_id_old:
                create_t.tag_id = tags[str(tag_id_old)]['id']

            # 2.5 绑定计划
            plan_id_old = task['plan_id']
            if plan_id_old:
                create_t.plan_id = plans[str(plan_id_old)].id

            # 2.4 从字符串解析时间对象
            time_add = strptime(task['time_add'])
            time_finish = strptime(task['time_finish'])
            create_t.time_add = time_add
            create_t.time_finish = time_finish

            db.session.add(create_t)

    def modify_user(uinfo):
        # 如果操作__dict__，不会同步到数据库
        user: User = Login.current_user() 
        user.email = uinfo['email']
        user.exp = uinfo['exp']
        user.introduce = uinfo['introduce']
        print('user success...')

    form = UpJsonForm()
    if form.validate_on_submit():
        # 1 解析json文件
        f = form.file.data.read() 
        f = json.loads(f)
        uinfo, books, tasks, tags, plans = f['user'], f['books'], f['tasks'], f['tags'], f['plans']

        user: User = Login.current_user() 
        user_old = {'email':user.email, 'exp':user.exp, 'introduce':user.introduce}
        data_old = [b for b in user.books] + [t for t in user.tasks] + [tag for tag in user.tags] + [plan for plan in user.plans]

        # 备注：错误被捕获之后，我不再知道是哪一行出错
        try:
            # 写新去旧
            create_tag(tags)
            create_book(books)
            create_plan(plans)
            db.session.commit()
            create_task(tasks, books, tags, plans)
            modify_user(uinfo)
            
            for item in data_old:
                db.session.delete(item)
            db.session.commit()
        except Exception as e:
            # 除新复旧
            user_db: User = Login.current_user()
            user_db.exp = user_old['exp']
            user_db.email = user_old['email']
            user_db.introduce = user_old['introduce']
            for item in [b for b in user.books] + [t for t in user.tasks] + [tag for tag in user.tags] + [plan for plan in user.plans]:
                db.session.delete(item)

            for item in data_old:
                db.session.add(item)
            db.session.commit()
            traceback.print_exc()  # 显示出错代码行
            print('导入数据失败...', type(e), e)
            flash('导入数据失败', 'danger')
            return redirect(url_for('.home'))

        flash('数据导入成功')
        return redirect(url_for('.home'))
    return render_template('auth/upload.html', form=form)


# ------------------------------ 三、好友社交  ------------------------------ #


def today_time(user: User):
    '''指定用户今天的学习时间'''
    now = datetime.utcnow()
    times = [t.use_minute for t in user.tasks if t.tfc.day == now.day 
             and t.time_finish.month == now.month 
             and t.time_finish.year == now.year]
    time = round(sum(times) / 60.0, 2) 
    return time


@auth_bp.route('/visit/<int:uid>')
@login_required
def visit(uid):
    '''拜访一个用户的主页'''
    # 备注：和home视图有重复
    # session['target_uid'] = uid
    user: User = User.query.get(uid)
    level = get_level(exp=user.exp)
    need_exp = get_exp(level + 1) - user.exp 
    return render_template('social/user.html', user=user, level=level, need_exp=need_exp)


@auth_bp.route('/users')
@login_required
def users():
    '''显示用户列表'''
    data = []
    users: list[User] = User.query.all()
    for u in users:
        if u.id == Login.current_id(): continue
        level = get_level(exp=u.exp)
        followed = Follow.query.filter(Follow.follower_id==Login.current_id(), Follow.followed_id==u.id).first()
        data.append({'user':u, 'name':u.name, 'level':level, 'introduce':u.introduce, 'time':today_time(u), 'avatar':u.avatar, 'followed':followed})        
    return render_template('social/users.html', users=data)


@auth_bp.route('/following')
@login_required
def following():
    '''自己关注的用户列表'''
    # 备注：和users代码相冗余，封装函数，或者用户类？
    data = []
    follows: list[Follow] = Login.current_user().following
    users = [f.followed for f in follows]
    for u in users:
        level = get_level(exp=u.exp)
        followed = Follow.query.filter(Follow.follower_id==Login.current_id(), Follow.followed_id==u.id).first()
        data.append({'user':u, 'name':u.name, 'level':level, 'introduce':u.introduce, 'time':today_time(u), 'avatar':u.avatar, 'followed':followed})        
    return render_template('social/following.html', users=data)


@auth_bp.route('/followers')
@login_required
def followers():
    '''粉丝列表'''
    # 备注：和users代码相冗余
    data = []
    follows: list[Follow] = Login.current_user().followers
    users = [f.follower for f in follows]
    for u in users:
        level = get_level(exp=u.exp)
        followed = Follow.query.filter(Follow.follower_id==Login.current_id(), Follow.followed_id==u.id).first()
        data.append({'user':u, 'name':u.name, 'level':level, 'introduce':u.introduce, 'time':today_time(u), 'avatar':u.avatar, 'followed':followed})        
    return render_template('social/followers.html', users=data)


@auth_bp.route('/follow/<int:uid>')
@login_required
def follow(uid):
    '''[API]关注'''
    current_id: User = Login.current_id()
    fl_ = Follow.query.filter(Follow.follower_id==current_id, Follow.followed_id==uid).first()
    if not fl_:
        fl = Follow(follower_id=current_id, followed_id=uid)
        db.session.add(fl)
        db.session.commit() 
    return jsonify({'success':True})


@auth_bp.route('/unfollow/<int:uid>')
@login_required
def unfollow(uid):
    '''[API]取消关注'''
    current_id: User = Login.current_id()
    fl_ = Follow.query.filter(Follow.follower_id==current_id, Follow.followed_id==uid).first()
    if fl_:
        db.session.delete(fl_)
        db.session.commit() 
    return jsonify({'success':True})


@auth_bp.route('/rank')
@login_required
def rank():
    '''当前用户的学习时间排行榜'''
    data = []
    user = Login.current_user()
    follows: list[Follow] = user.following
    users = [f.followed for f in follows] + [user]
    for u in users:
        level = get_level(exp=u.exp)
        data.append({'name':u.name, 'level':level, 'time':today_time(u), 'id':u.id})    
    data.sort(key=lambda x:x['time'], reverse=True)
    return jsonify(data)
