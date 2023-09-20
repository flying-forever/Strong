from flask import render_template, redirect, url_for, session, Blueprint, make_response, request
from wtforms import BooleanField

from strong.callbacks import login_required
from strong.utils import flash_ as flash
from strong.forms import LoginForm
from strong.models import User
from strong import db


# ------------------------------ 一、用户模块 ------------------------------ #


auth_bp = Blueprint('auth', __name__, static_folder='static', template_folder='templates')


@auth_bp.before_request
def remenber_login():
    user_id: str = request.cookies.get('remenber_user') 

    # 若没有登录，则自动登录
    if user_id and not session['uid']: 
        user = User.query.get(user_id)

        session['uid'] = user.id
        session['uname'] = user.name
        print('已自动登录... ', user)
    

@auth_bp.route('/')
@auth_bp.route('/home')
@login_required
def home():
    print('home...')
    user = User.query.get(session['uid'])
    return render_template('auth/home.html', user=user)


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
            # 登录成功
            session['uid'] = user.id
            session['uname'] = user.name
            
            # 使用cookie记住登录
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
    session['uid'] = None
    session['uname'] = None

    # 并删除“记住登录”状态
    response = make_response(redirect(url_for('.login')))
    response.set_cookie('remenber_user', ''.encode('utf-8'), max_age=0)

    return response
    