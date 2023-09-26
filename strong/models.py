from datetime import datetime
from flask import session

from strong import db

class Task(db.Model):
    """任务模型"""
    id = db.Column(db.Integer, primary_key=True) # 任务编号

    # 创建任务
    name = db.Column(db.String(64), nullable=False) # 任务名
    exp = db.Column(db.Integer, nullable=False) # 经验值
    need_minute = db.Column(db.Integer, nullable=False, default=0) # 任务预计时间 | mapped_column默认不能为null
    task_type = db.Column(db.Integer, nullable=False, default=0) # 0 一次任务，1 重复任务；

    # 提交任务
    describe = db.Column(db.String(256), nullable=False, default='') # 随笔
    is_finish = db.Column(db.Boolean, nullable=False, default=False) # True为已完成
    use_minute = db.Column(db.Integer, nullable=False, default=0) # 完成任务耗时（分钟）

    # 自动时间戳
    time_add = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    time_finish = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键与关系属性
    uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='tasks')

    def __str__(self) -> str:
        return f"<Task name='{self.name}' exp={self.exp}>"


class User(db.Model):
    """用户模型
    - 集成了一些基于session的用户操作"""

    id = db.Column(db.Integer, primary_key=True) # 用户编号
    name = db.Column(db.String(64), nullable=False, unique=True) # 用户昵称
    password = db.Column(db.String(64), nullable=False) # 登录密码
    exp = db.Column(db.Integer, nullable=False, default=0) # 该用户总经验值

    time_add = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # 账号创建时间

    tasks = db.relationship('Task', back_populates='user')

    def __str__(self) -> str:
        return f"<Task id={self.id} name='{self.name}' exp={self.exp}>"

    def login(self):
        # 疑惑：是否会破坏数据层与业务逻辑的分离呢？有必要和User类耦合在一切吗？
        session['uid'] = self.id
        session['uname'] = self.name
        print(f"- 已登录用户：<{session['uid']},{session['uname']}>")
    
    def logout():
        # 疑惑：没用@staticmethod装饰器，也可以通过类直接调用
        print(f"- 已退出用户：<{session['uid']},{session['uname']}>")
        session['uid'] = None
        session['uname'] = None

    def is_login():
        return bool(session['uid'])

    def current_user():
        """通过会话从数据库查询并返回当前用户"""
        return User.query.get(session['uid'])

    def current_id():
        return session['uid']
    
    def current_name():
        return session['uname']
