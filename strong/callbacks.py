from flask import session, flash, redirect, url_for
from functools import wraps
from strong import app


@app.before_first_request
def first():
    """初始化session，防止出现KeyError。"""
    print('init the uid and uname of first...')
    session['uid'] = None
    session['uname'] = None


# 装饰器：要求视图函数登录才能访问
def login_required(func):
    """装饰器：要求视图函数登录才能访问"""

    @wraps(func)
    def decorated(*args, **kwargs):
        print('this is decorated of login_required...')
        if session['uid'] is None:
            flash('请先登录！')
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return decorated