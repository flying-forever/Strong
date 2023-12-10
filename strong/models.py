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
    time_finish: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 外键与关系属性
    uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='tasks')

    bid = db.Column(db.Integer, db.ForeignKey('book.id'))
    book = db.relationship('Book', back_populates='tasks') # 注：一对一关系

    def __str__(self) -> str:
        return f"<Task name='{self.name}' exp={self.exp}>"


class User(db.Model):
    """用户模型
    - 集成了一些基于session的用户操作"""

    id = db.Column(db.Integer, primary_key=True) # 用户编号
    name = db.Column(db.String(64), nullable=False, unique=True) # 用户昵称
    password = db.Column(db.String(64), nullable=False) # 登录密码
    exp = db.Column(db.Integer, nullable=False, default=0) # 该用户总经验值
    introduce = db.Column(db.String(128), nullable=False, default='空空如也') # 个人简介 
    email = db.Column(db.String(64), nullable=False, default='None') # 电子邮件
    avatar = db.Column(db.String(64), nullable=True) # 头像

    time_add = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # 账号创建时间

    tasks = db.relationship('Task', back_populates='user')
    books = db.relationship('Book', back_populates='user')

    def __str__(self) -> str:
        return f"<User id={self.id} name='{self.name}' exp={self.exp}>"


class Book(db.Model):
    """书籍模型
    @create: name, page, uid\n"""
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False) # 书名
    page = db.Column(db.Integer, nullable=False) # 总页数
    cover = db.Column(db.String(64), nullable=True) # 封面

    tasks = db.relationship('Task', back_populates='book')

    uid = db.Column(db.Integer, db.ForeignKey('user.id'))  # 怀疑：其实可以通过tid间接找到uid？
    user = db.relationship('User', back_populates='books')

