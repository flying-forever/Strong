from strong import app


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


@app.context_processor
def make_template_context():
    """增加模板上下文变量"""
    return dict(TaskOrder=TaskOrder)


def order_query_by(query, field, is_desc=True):
    """
    好像没什么用
    @params
    - query：待排序的查询对象，来自数据库
    - field：排序依据字段
    - is_desc -> bool：默认（True）为倒序"""
    if is_desc:
        ordered_query = query.order_by(field.desc())
