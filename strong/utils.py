import math, os, uuid
from flask import flash, session
from strong.models import User


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


class Clf:
    # data中将task和tag展示到图，task加上偏移避免id冲突。在修改图中的tag时，也要用到它判断id是task|tag
    idOffset = 123456789


def flash_(message: str, category='success'):
    """- 使flash有一个默认的样式分类：success"""
    flash(message=message, category=category)


def get_level(exp: int):
    """经验值 --> 对应等级"""
    return int(math.sqrt(exp * 2 + 0.25) - 0.5)  # ceil向上取整（已对边界值测试）

def get_exp(level: int):
    """等级 --> 对应经验值"""
    return int((level * level + level) / 2)


def random_filename(filename):
    """生成随机的文件名，防止用户上传的文件名中带有恶意路径。"""
    ext = os.path.splitext(filename)[1]
    new_filename = uuid.uuid4().hex + ext   # 疑惑：uuid的原理？
    return new_filename
