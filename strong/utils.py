from dataclasses import dataclass
import math, os, uuid, time
from PIL import Image
from datetime import datetime, timedelta

from flask import flash, session, current_app
from strong.models import User, Task


class Time:
    """表示时间长度（而不是日期）"""

    def __init__(self, hours:int=0, minutes:int=0) -> None:
        self.hours = hours
        self.minutes = minutes
        self.standard()

    def standard(self):
        """将实例的时间字段标准化（如分钟位范围位0~59）"""
        while self.minutes > 59:
            self.minutes -= 60
            self.hours += 1

    def get_minutes_all(self):
        return self.hours * 60 + self.minutes

    def get_hours_all(self):
        """返回值可能是小数"""
        return self.hours + self.minutes / 60

    # 重构：改用运算符重载如何？
    def add(self, time=None, hours:int=0, minutes:int=0):
        """
        @params
        - time: 该Time类的对象。提供time参数时，后面的hours, minutes参数不生效。
        - 注：不修改原对象，而是返回一个新的对象。"""
        result = self
        if time:
            result.hours += time.hours
            result.minutes += time.minutes
        else:
            result.hours += hours
            result.minutes += minutes
        result.standard()
        return result

    def __str__(self) -> str:
        return f"{self.hours}h {self.minutes}m"


class TaskOrder:
    """
    参照Task数据库模型 - 给排序方式编号
    @attribute
    - 属性有“完整名”和“简写”两种形式，如“FD”是“FINISH_DESC”的简写

    @problem
    - 用单例模式又如何？"""

    FD = FINISH_DESC = 1
    FA = FINISH_ASC = 2
    AD = ADD_DESC = 3
    AA = ADD_ASC = 4
    ND = NAME_DESC = 5
    NA = NAME_ASC = 6


class Login:
    """登录模块的session操作集成"""

    # 类方法的简化定义 --> 缺点：1、不能编写文档, 2、不能操作类实例属性, 3、不便于类型推断。
    is_login = lambda : bool(session['uid'])
    current_id: int = lambda : session['uid']
    current_name: str = lambda : session['uname']
    current_user: User = lambda: User.query.get(session['uid']) # 怀疑：是否会对性能影响较大？

    def login(user):
        # 疑惑：是否会破坏数据层与业务逻辑的分离呢？有必要和User类耦合在一切吗？
        session['uid'] = user.id
        session['uname'] = user.name
        print(f"- 已登录用户：<{session['uid']},{session['uname']}>") 
        
    def logout():
        # 疑惑：没用@staticmethod装饰器，也可以通过类直接调用
        print(f"- 已退出用户：<{session['uid']},{session['uname']}>")
        session['uid'] = None
        session['uname'] = None


def flash_(message: str, category='success'):
    """- 使flash有一个默认的样式分类：success"""
    flash(message=message, category=category)

# 批注：感觉这样的方法设计得很不“面向对象”
def get_level(exp: int):
    """经验值 --> 对应等级"""
    return int(math.sqrt(exp * 2 + 0.25) - 0.5)  # ceil向上取整（已对边界值测试）


def get_exp(level: int):
    """等级 --> 对应经验值"""
    return int((level * level + level) / 2)


def random_filename(filename) -> str:
    """生成随机的文件名，防止用户上传的文件名中带有恶意路径。"""
    ext = os.path.splitext(filename)[1]
    new_filename = uuid.uuid4().hex + ext   # 疑惑：uuid的原理？
    return new_filename


def save_file(file):
    '''保存图片文件，返回filename。把文件名(而非路径)写入数据库 —— 文件所在路径将是可变的'''
    # 备注：到底要不要裁剪呢？
    img = Image.open(file)

    # 裁剪中心的正方形一块
    x, y = img.size
    small_edge = min(x, y)
    left_top = (x // 2 - small_edge // 2, y // 2 - small_edge // 2)
    right_bottom = (x // 2 + small_edge // 2, y // 2 + small_edge // 2)
    img = img.crop((*left_top, *right_bottom))

    rsize = ( min(500, img.size[0]), min(500, img.size[1]) )
    img = img.resize(rsize,  Image.LANCZOS)  # 会保持比例，LANCZOS是高质量上采样
    filename = random_filename(file.filename)
    img.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
    return filename


def _test_time(func, *args):
    # 备注：也许可以写成装饰器？
    stime = time.time()
    r = func(*args)

    use_time = time.time() - stime
    print(f'{use_time:.4}秒')
    return r


@dataclass
class TaskDossier:
    name: str
    hour: float=0
    count: int=0


def get_dossier(tasks: list[Task], sort: str=None):
    '''@sort: 默认按任务完成时间排序。'hour'按累积小时排序'''
    
    d = {}
    for t in tasks:
        if t.name not in d:
            d[t.name] = TaskDossier(t.name)
        ds = d[t.name]
        ds.hour += t.use_minute / 60
        ds.count += 1
    dses = list(d.values())
    for ds in dses:
        ds.hour = round(ds.hour, 2)
    if sort == 'hour':
        dses.sort(key=lambda ds: ds.hour, reverse=True)
    return dses


def task_to_dict(task: Task):
    return {
        'id': task.id,
        'name': task.name,
        'is_finish': task.is_finish,
        'time_finish': (task.time_finish + timedelta(hours=8)).strftime(r'%Y-%m-%d %H:%M:%S'),
        'hour': round(task.use_minute / 60, 2),
        'describe': task.describe,

        'exp': task.exp,
        'need_minute': task.need_minute,
    }


def recently_tasks(days: int, uid: int):
    '''最近days天的已完成任务'''

    tasks: list[Task] = Task.query.filter_by(uid=uid, is_finish=True).order_by(Task.time_add.desc()).all()

    _f = lambda t : abs(t.tfc.date() - (datetime.utcnow() + timedelta(hours=8)).date()) < timedelta(days=days)
    tasks = [t for t in tasks if _f(t)]
    return tasks
