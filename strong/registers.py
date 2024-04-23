from flask import redirect, url_for, flash, get_flashed_messages
from wtforms import BooleanField


def register_index(app):
    @app.route('/')
    def index():
        # 设置session的过期时间，默认为30天
        from flask import session
        session.permanent = True
        return redirect(url_for('auth.home'))


def register_context(app):
    @app.context_processor
    def make_template_context():
        """增加模板上下文变量"""
        return dict(BooleanField=BooleanField, isinstance=isinstance)


def register_getfile(app):
    @app.route('/getfile/<path:filename>')
    def getfile(filename):
        '''为访问用户上传的文件，提供一个端点'''
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_PATH'], filename)


def register_move_site(app):
    if 'NEW_SITE' in app.config: 
        @app.before_request
        def web_move_m():
            new_site = app.config['NEW_SITE']
            get_flashed_messages()  # 清空栈，保持仅一条消息
            flash(f"本站点服务器将在5月30日到期，数据不再同步。请转到 {new_site}", category='danger')
