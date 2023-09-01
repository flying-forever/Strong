from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class TaskForm(FlaskForm):
    """创建任务的表单"""
    name = StringField(label='任务名称', validators=[DataRequired('不能为空')])
    exp = IntegerField(label='经验值', validators=[NumberRange(1, 5, '单个任务经验值范围为1~5'), DataRequired('不能为空')])
    submit = SubmitField(label='确定')


class TaskSubmitForm(FlaskForm):
    """提交任务，并填写完成效果的表单"""
    describe = StringField(label='完成效果', validators=[DataRequired('不能为空')])
    submit = SubmitField(label='确定')
    