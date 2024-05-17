import datetime, re

from flask import render_template, redirect, url_for, Blueprint

from strong.utils import Time, Login, save_file
from strong.utils import flash_ as flash
from strong.forms import BookForm, UploadForm
from strong.models import Task, Book
from strong import db


book_bp = Blueprint('book', __name__, static_folder='static', template_folder='templates')


def bind(taskname, book_id):
    '''将匹配的任务绑定到书籍，并db.session.commit()'''
    tasks: list[Task] = Task.query.filter(Task.name.like(f'%{taskname}%'), Task.uid==Login.current_id()).all()
    for task in tasks:
        if task.bid is None:
            task.bid = book_id
    db.session.commit()


@book_bp.route('/bookcase')
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


@book_bp.route('/bookcase/create', methods=['GET', 'POST'])
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


@book_bp.route('/bookcase/update/<int:book_id>', methods=['GET', 'POST'])
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


@book_bp.route('/bookcase/unbind/<taskname>/<int:book_id>')
def book_unbind(taskname, book_id):
    un_tasks = Task.query.filter(Task.name==taskname, Task.uid==Login.current_id()).all() # 问题：怎么这个.all()要不要都一样
    for task in un_tasks:
        task.bid=None
    db.session.commit()
    return redirect(url_for('.book_update', book_id=book_id))


@book_bp.route('/bookcase/delete/<int:book_id>')
def book_delete(book_id):
    book = Book.query.filter(Book.id==book_id, Book.uid==Login.current_id()).first()
    db.session.delete(book) # 注：默认的级联操作，会自动删除task中对应的外键
    db.session.commit()
    flash('删除成功')
    return redirect(url_for('.bookcase'))


@book_bp.route('/upload_cover/<int:book_id>', methods=['GET','POST'])
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

