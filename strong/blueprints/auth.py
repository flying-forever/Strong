from flask import render_template, redirect, url_for, session, Blueprint, make_response, request, current_app
from flask import send_from_directory

import os

from strong.callbacks import login_required
from strong.utils import Login, get_level, get_exp, random_filename
from strong.utils import flash_ as flash
from strong.forms import LoginForm, UserForm, UploadForm
from strong.models import User
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
    