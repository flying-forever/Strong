from flask import session, flash, redirect, url_for
from functools import wraps
from strong import app
from strong.utils import TaskOrder


def login_required(func):
    """装饰器：要求视图函数登录才能访问"""

    @wraps(func)
    def decorated(*args, **kwargs):
        print('this is decorated of login_required...')
        if session.get('uid', None) is None:
            flash('请先登录！')
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return decorated


@app.context_processor
def make_template_context():
    """增加模板上下文变量"""
    return dict(TaskOrder=TaskOrder)
