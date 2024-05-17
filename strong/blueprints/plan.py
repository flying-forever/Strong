import datetime

from flask import render_template, redirect, url_for, Blueprint

from strong.callbacks import login_required
from strong.utils import Login, save_file
from strong.utils import flash_ as flash
from strong.forms import UploadForm, PlanForm
from strong.models import Task, Plan
from strong import db
# 重构：在蓝本上统一注册装饰器

# ------------------------------ 一、基础模块 ------------------------------ #


plan_bp = Blueprint('plan', __name__, static_folder='static', template_folder='templates')


@plan_bp.before_request
@login_required
def login_protect():
    pass


# ------------------------------ 计划模块 ------------------------------ #


@plan_bp.route('/plan/create', methods=['GET', 'POST'], endpoint='plan_create')
@plan_bp.route('/plan/update/<int:plan_id>', methods=['GET', 'POST'], endpoint='plan_update')
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


@plan_bp.route('/plan/unbind/<taskname>/<int:plan_id>')
def plan_unbind(taskname, plan_id):
    # 计划的子任务提交几次后，这解绑的影响是不可逆的，因为每种任务都是“部分”绑定到计划
    un_tasks = Task.query.filter(Task.plan_id==plan_id, Task.name==taskname, Task.uid==Login.current_id()).all() # 问题：怎么这个.all()要不要都一样
    for task in un_tasks:
        task.plan_id=None
    db.session.commit()
    return redirect(url_for('.plan_update', plan_id=plan_id))


@plan_bp.route('/plan/end/<int:plan_id>')
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


@plan_bp.route('/plan/restart/<int:plan_id>')
def plan_restart(plan_id):
    plan = Plan.query.get(plan_id)
    plan.is_end = False
    db.session.commit()
    flash('复活成功')
    return redirect(url_for('.plans'))


@plan_bp.route('/plan/delete/<int:plan_id>')
def plan_delete(plan_id):
    plan = Plan.query.filter(Plan.id==plan_id, Login.current_id()==Plan.uid).first()
    db.session.delete(plan)
    db.session.commit()
    flash('删除成功')
    return redirect(url_for('.plans'))


@plan_bp.route('/plans')
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


@plan_bp.route('/plan/cover/<int:plan_id>', methods=['GET', 'POST'])
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

