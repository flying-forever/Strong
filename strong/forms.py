from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, NumberRange


class TaskForm(FlaskForm):
    """创建任务的表单"""
    name = StringField(label='任务名称', validators=[DataRequired('不能为空')])
    exp = IntegerField(label='经验值', validators=[NumberRange(1, 5, '单个任务经验值范围为1~5'), DataRequired('不能为空')])
    need_minute = IntegerField(label='预计用时(m)', validators=[NumberRange(0, float("inf"), '应为正整数')], default=30)
    task_type = SelectField(label='任务类型', choices=[(0, '一次任务'), (1, '重复任务')], default=0)
    submit = SubmitField(label='确定')


# 重构：表单只填写分钟数
class TaskSubmitForm(FlaskForm):
    """提交任务，并填写完成效果的表单"""
    describe = StringField(label='完成效果', validators=[DataRequired('不能为空')])
    use_hour = IntegerField(label='消耗小时数', validators=[NumberRange(0, float("inf"), '应为正整数')], default=0)
    use_minute = IntegerField(label='消耗分钟数', validators=[NumberRange(0, float("inf"), '应为正整数'), DataRequired('不能为空')])
    submit = SubmitField(label='确定')
    

class LoginForm(FlaskForm):
    """
    登录表单
    - 注：暂时复用为注册表单，后期可能要改"""
    username = StringField(label='用户名', validators=[DataRequired('不能为空')])
    password = StringField(label='密码', validators=[DataRequired('不能为空')])
    remenber = BooleanField(label='记住我', default=False)
    submit = SubmitField(label='确定')
