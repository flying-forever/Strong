from datetime import datetime
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Integer

from strong import db

class Task(db.Model):
    """任务模型"""

    id = db.Column(db.Integer, primary_key=True) # 任务编号
    name = db.Column(db.String(64), nullable=False) # 任务名
    exp = db.Column(db.Integer, nullable=False) # 经验值

    describe = db.Column(db.String(256), nullable=False, default='') # 随笔
    is_finish = db.Column(db.Boolean, nullable=False, default=False) # True为已完成

    time_add = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    time_finish = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    need_minute: Mapped[int] = mapped_column(Integer, default=0) # 任务预计时间 | mapped_column默认不能为null
    use_minute = db.Column(db.Integer, nullable=False, default=0) # 完成任务耗时（分钟）

    uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='tasks')

    def __str__(self) -> str:
        return f"<Task name='{self.name}' exp={self.exp}>"


class User(db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True) # 用户编号
    name = db.Column(db.String(64), nullable=False, unique=True) # 用户昵称
    password = db.Column(db.String(64), nullable=False) # 登录密码
    exp = db.Column(db.Integer, nullable=False, default=0) # 该用户总经验值

    time_add = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # 账号创建时间

    tasks = db.relationship('Task', back_populates='user')

    def __str__(self) -> str:
        return f"<Task id={self.id} name='{self.name}' exp={self.exp}>"
