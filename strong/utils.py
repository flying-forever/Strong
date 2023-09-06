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
