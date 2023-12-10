from flask import redirect, url_for
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
