from strong.blueprints.auth import auth_bp
from strong.blueprints.data import data_bp
from strong.blueprints.task import task_bp
from strong.blueprints.book import book_bp
from strong.blueprints.plan import plan_bp
from strong.blueprints.tag import tag_bp

from strong.callbacks import login_required


# 批量为蓝本添加登录保护
protects = [task_bp, data_bp, book_bp, plan_bp, tag_bp]
for bp in protects:
    @bp.before_request
    @login_required
    def login_protect():
        pass
