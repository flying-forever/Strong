from flask import session, flash, redirect, url_for
from functools import wraps


def login_required(func):
    """装饰器：要求视图函数登录才能访问"""

    @wraps(func)
    def decorated(*args, **kwargs):
        print('this is decorated of login_required...')
        if session.get('uid', None) is None:
            flash('请先登录！', 'danger')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)

    return decorated
