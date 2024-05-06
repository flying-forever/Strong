import datetime, re, os

from flask import render_template, redirect, url_for, session, Blueprint, request, current_app, jsonify

from strong.callbacks import login_required
from strong.utils import Time, TaskOrder, Login, random_filename, Clf
from strong.utils import flash_ as flash
from strong.forms import TaskForm, TaskSubmitForm, BookForm, UploadForm, PlanForm
from strong.models import User, Task, Book, Tag, Plan
from strong import db
# 重构：在蓝本上统一注册装饰器

# ------------------------------ 一、基础模块 ------------------------------ #


task_bp = Blueprint('task', __name__, static_folder='static', template_folder='templates')


@task_bp.before_request
@login_required
def login_protect():
    """为整个视图添加登录保护"""
    pass


@task_bp.context_processor
def make_template_context():
    """增加模板上下文变量"""
    return dict(TaskOrder=TaskOrder)


def save_file(file):
    '''返回filename'''
    filename = random_filename(file.filename)
    file.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
    return filename


# ------------------------------ 二、任务模块 ------------------------------ #


@task_bp.route('/')
@task_bp.route('/doing')
def task_doing():
    tasks: list[Task] = Task.query.filter_by(uid=Login.current_id()).order_by(Task.time_add.desc()).all() # 时间逆序
    tasks = [task for task in tasks if not task.is_finish] # 待完成的任务列表
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


@task_bp.route('/submit/<int:task_id>', methods=['GET', 'POST'])
def task_submit(task_id):
    """提交/修改任务的视图"""
    
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
            plan = Plan.query.get(task.plan_id)
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
    form.describe.data = task.describe
    
    return render_template('task/task_submit.html', form=form, task=task)


@task_bp.route('/delete/<int:task_id>')
def task_delete(task_id):
    task = Task.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('成功删除任务！')
    return redirect(url_for('.task_doing'))


# ------------------------------ 三、书架模块 ------------------------------ #


def bind(taskname, book_id):
    '''将匹配的任务绑定到书籍，并db.session.commit()'''
    tasks: list[Task] = Task.query.filter(Task.name.like(f'%{taskname}%'), Task.uid==Login.current_id()).all()
    for task in tasks:
        if task.bid is None:
            task.bid = book_id
    db.session.commit()


@task_bp.route('/bookcase')
def bookcase():
    def page_form_str(in_str):
        '''从字符串中提取页数信息，用正则表达式'''

        targets = [r'p(\d+)', r'(\d+)页']
        matchs = [re.search(target, in_str) for target in targets]
        for match in matchs:
            if match:
                return int(match.group(1))
        return 0

    def read_page(book: Book):
        '''获取书籍已读页数'''
        # 重构：低效实现，每本书都会执行一次查询
        tasks: list[Task] = book.tasks
        read_pages = [page_form_str(task.describe) for task in tasks]
        return max(read_pages) if read_pages else 0

    def read_hour(book: Book):
        '''获取书籍已读时间'''
        minute = 0
        tasks: list[Task] = book.tasks 
        for task in tasks:
            minute += task.use_minute 
        hour = round(minute / 60.0, 2) # 保留两位小数
        return hour

    def book_recent(book: Book):
        '''获取book的最近阅读时间'''
        early = datetime.datetime(2022,1,1)  # 一个早在系统之前的时间
        times = [task.time_finish for task in book.tasks]
        recent = max(times) if times else early
        return recent


    books: list[Book] = Book.query.filter(Book.uid==Login.current_id()).all()

    # 备注：字典的扩展性似乎不错
    books_show = [{'id':book.id, 'name':book.name, 'page':book.page, 'cover':book.cover, \
        'read_page':read_page(book), 'percent':0, 'read_hour':read_hour(book), 'recent': book_recent(book)}
        for book in books]
    books_show.sort(key=lambda x:x['recent'], reverse=True)  # 按“最近使用”排序

    for book in books_show:
        book['percent'] = round(100 * book['read_page'] / book['page'], 2)
    return render_template('task/bookcase.html', books=books_show, Time=Time)


@task_bp.route('/bookcase/create', methods=['GET', 'POST'])
def book_create():
    form = BookForm()
    if form.validate_on_submit():
        # 补充：判断书名对当前用户是否重复
        book = Book(name=form.bookname.data, page=form.page.data, uid=Login.current_id())
        db.session.add(book)
        db.session.commit()  # 问题：因为是新任务，所以要先提交后，才能与词条绑定。但这里细节还不太理解

        # 自动创建同名任务
        c_task = form.c_task.data
        if c_task:
            # 备注：应让用户可填写更好
            task = Task(name=f'《{form.bookname.data}》', exp=1, need_minute=30, \
                uid=Login.current_id(), task_type=1)
            task.bid = book.id
            db.session.add(task)
            db.session.commit()
            
        # 任务绑定
        bind(taskname=form.taskname.data, book_id=book.id)

        flash('书籍创建成功！')
        return redirect(url_for('.bookcase'))
    return render_template('task/book_create.html', form=form)


@task_bp.route('/bookcase/update/<int:book_id>', methods=['GET', 'POST'])
def book_update(book_id):
    form = BookForm()
    book: Book = Book.query.get(book_id)
    if form.validate_on_submit():
        
        # 基本信息修改
        book.name = form.bookname.data
        book.page = form.page.data

        # 任务绑定
        bind(taskname=form.taskname.data, book_id=book.id)
        
        flash('修改成功！')
        return redirect(url_for('.book_update', book_id=book_id))

    # 回显表单
    bind_tasknames = list(set(t.name for t in book.tasks))
    form.bookname.data = book.name 
    form.page.data = book.page

    #重构：book_id使在book_unbind中能跳回来，有没有更优雅的重定向方式？
    return render_template('task/book_create.html', form=form, bind_tasknames=bind_tasknames, book_id=book_id)


@task_bp.route('/bookcase/unbind/<taskname>/<int:book_id>')
def book_unbind(taskname, book_id):
    un_tasks = Task.query.filter(Task.name==taskname, Task.uid==Login.current_id()).all() # 问题：怎么这个.all()要不要都一样
    for task in un_tasks:
        task.bid=None
    db.session.commit()
    return redirect(url_for('.book_update', book_id=book_id))


@task_bp.route('/bookcase/delete/<int:book_id>')
def book_delete(book_id):
    book = Book.query.filter(Book.id==book_id, Book.uid==Login.current_id()).first()
    db.session.delete(book) # 注：默认的级联操作，会自动删除task中对应的外键
    db.session.commit()
    flash('删除成功')
    return redirect(url_for('.bookcase'))


@task_bp.route('/upload_cover/<int:book_id>', methods=['GET','POST'])
def upload_cover(book_id):
    '''为书籍上传封面'''
    book: Book = Book.query.filter(Book.id==book_id, Book.uid==Login.current_id()).first()
    form = UploadForm()
    if form.validate_on_submit():
        book.cover = save_file(file=form.photo.data)
        db.session.commit()
        flash('上传成功！')
        return redirect(url_for('.bookcase'))
    return render_template('auth/upload.html', form=form)


# ------------------------------ 四、标签模块 api ------------------------------ #


def tag_create(tag_name, pid, uid, **kwargs):
    '''重名 -> False'''
    tag = Tag.query.filter(Tag.name==tag_name, Tag.uid==uid).first()
    if tag is not None: return False
    tag = Tag(name=tag_name, uid=uid, pid=pid)
    db.session.add(tag)
    db.session.commit()
    return True

def tag_update(tag_id, tag_name, pid, uid, **kwargs):
    # 备注：这样好像太灵活，比如传入一个找不到的pname，也会将父节点置空
    tag = Tag.query.filter(Tag.id==tag_id, Tag.uid==uid).first()
    tag.name = tag_name
    tag.pid = pid
    db.session.commit()
    return True

def task_bind_update(task_name, pid, uid, **kwargs):
    '''pid: int | None  (服务器python太老，不支持这样注解)'''
    print('task_name:', task_name, 'pid:', pid)
    tasks = Task.query.filter(Task.name==task_name, Task.uid==uid).all()
    # print('tasks,', tasks)
    for t in tasks:
        t.tag_id = pid
    db.session.commit()
    return True

@task_bp.route('/tag/node', methods=['GET', 'POST'])
def tag_node():
    # 1 解析数据:str | '' | None
    print('form:', request.form)
    node_id = request.form.get('tagid')
    name = request.form.get('tagname').strip()
    pname = request.form.get('pname')

    uid = Login.current_id()
    pid = Tag.query.filter(Tag.name==pname, Tag.uid==uid).first().id if pname else None

    # 2 判断操作类型
    ops = [tag_create, tag_update, task_bind_update]
    messages = ['创建出错，标签名不能重复', '标签更新出错', '任务绑定出错']
    if '' == node_id:
        op = 0
    elif int(node_id) < Clf.idOffset:
        op = 1
    else:
        op = 2
    res = {}
    res['success'] = ops[op](uid=uid, tag_id=node_id, pid=pid, tag_name=name, task_name=name)
    res['message'] = messages[op] if not res['success'] else ''
    return jsonify(res)
    

@task_bp.route('/tag/delete', methods=['GET', 'POST'])
def tag_delete():
    '''异步删除标签'''
    # 如果是task，id偏移很大，反正在数据库也查不到
    res = {'success':True, 'message':'...'}
    tagid = request.form.get('tagid')
    tag = Tag.query.filter(tagid==Tag.id, Login.current_id()==Tag.uid).first()
    if tag:
        db.session.delete(tag)
        db.session.commit()
    else:
        res['success'] = False
    return jsonify(res)


# ------------------------------ 五、计划模块 ------------------------------ #


@task_bp.route('/plan/create', methods=['GET', 'POST'], endpoint='plan_create')
@task_bp.route('/plan/update/<int:plan_id>', methods=['GET', 'POST'], endpoint='plan_update')
def plan_create(plan_id=None):
    '''创建/更新计划'''
    # 备注：可以拆一下
    # 备注：没验证用户身份（修改别人数据）

    form = PlanForm()
    def gfd(name: str):
        '''备注：简化参数传递的尝试'''
        return form.__dict__[name].data
    
    def bind_tp(taskname: str):
        tasks: Task = Task.query.filter(Task.uid==Login.current_id(), False==Task.is_finish, Task.name.like(f'%{taskname}%') ).all()
        for task in tasks:
            if task.plan_id is None:
                task.plan_id = plan.id
        db.session.commit()

    if form.validate_on_submit():
        if plan_id is None:
            # 创建
            plan = Plan(name=gfd('name'), need_minute=gfd('need_minute'), uid=Login.current_id())
            db.session.add(plan)
            db.session.commit()
            bind_tp(gfd('taskname'))
            return redirect(url_for('.plans'))
        else:
            # 更新
            plan = Plan.query.get(plan_id)
            plan.name = gfd('name')
            plan.need_minute = gfd('need_minute')
            bind_tp(gfd('taskname'))
            flash('修改成功')
            return redirect(url_for('.plan_update', plan_id=plan_id))
    # 表单回显
    bind_tasknames = []
    if plan_id:
        plan = Plan.query.get(plan_id)
        bind_tasknames = list(set(t.name for t in plan.tasks))
        form.name.data = plan.name
        form.need_minute.data = plan.need_minute
    return render_template('task/plan_form.html', form=form, bind_tasknames=bind_tasknames, plan_id=plan_id)


@task_bp.route('/plan/unbind/<taskname>/<int:plan_id>')
def plan_unbind(taskname, plan_id):
    # 计划的子任务提交几次后，这解绑的影响是不可逆的，因为每种任务都是“部分”绑定到计划
    un_tasks = Task.query.filter(Task.plan_id==plan_id, Task.name==taskname, Task.uid==Login.current_id()).all() # 问题：怎么这个.all()要不要都一样
    for task in un_tasks:
        task.plan_id=None
    db.session.commit()
    return redirect(url_for('.plan_update', plan_id=plan_id))


@task_bp.route('/plan/end/<int:plan_id>')
def plan_end(plan_id):
    plan = Plan.query.get(plan_id)
    plan.is_end = True
    plan.end_time = datetime.datetime.utcnow()
    # 与未完成的任务解绑
    for t in plan.tasks:
        if not t.is_finish:
            t.plan_id = None
    db.session.commit()
    flash('提交成功')
    return redirect(url_for('.plans'))


@task_bp.route('/plan/restart/<int:plan_id>')
def plan_restart(plan_id):
    plan = Plan.query.get(plan_id)
    plan.is_end = False
    db.session.commit()
    flash('复活成功')
    return redirect(url_for('.plans'))


@task_bp.route('/plan/delete/<int:plan_id>')
def plan_delete(plan_id):
    plan = Plan.query.filter(Plan.id==plan_id, Login.current_id()==Plan.uid).first()
    db.session.delete(plan)
    db.session.commit()
    flash('删除成功')
    return redirect(url_for('.plans'))


@task_bp.route('/plans')
def plans():
    plans = Plan.query.filter(Login.current_id()==Plan.uid).all()
    for plan in plans:
        plan: Plan
        plan.use_hour = plan.use_hour()  # 备注：在db.Model实现的，咋样？
        plan.need_hour = round(plan.need_minute / 60, 2)
        plan.percent = round(plan.use_hour / plan.need_hour * 100, 2)
    plans_doing = [p for p in plans if not p.is_end]
    plans_done = [p for p in plans if p.is_end]
    # 备注：可能dict比对象更 显式
    return render_template('task/plans.html', plans=plans, plans_doing=plans_doing, plans_done=plans_done)


@task_bp.route('/plan/cover/<int:plan_id>', methods=['GET', 'POST'])
def plan_cover(plan_id):
    '''为计划上传封面'''
    plan: Plan = Plan.query.filter(Plan.id==plan_id, Plan.uid==Login.current_id()).first()
    form = UploadForm()
    if form.validate_on_submit():
        plan.cover = save_file(file=form.photo.data)
        db.session.commit()
        flash('上传成功！')
        return redirect(url_for('.plans'))
    return render_template('auth/upload.html', form=form)


# ------------------------------ 六、胡乱尝试 ------------------------------ #


@task_bp.route('/test')
def test():
    """用于尝试一些新功能，或样式。"""
    return render_template('_test.html')
