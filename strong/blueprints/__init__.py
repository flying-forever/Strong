from strong.blueprints.auth import auth_bp
from strong.blueprints.data import data_bp
from strong.blueprints.task import task_bp
from strong.blueprints.p_book import book_bp
from strong.blueprints.p_plan import plan_bp
from strong.blueprints.p_tag import tag_bp
# from strong.blueprints.trys import try_bp

from strong.wraps import login_required


# 批量为蓝本添加登录保护
protects = [task_bp, data_bp, book_bp, plan_bp, tag_bp]
for bp in protects:
    @bp.before_request
    @login_required
    def login_protect():
        pass

# from flask_cors import CORS
# CORS(auth_bp)
# CORS(plan_bp)