from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, SubmitField, SelectField, BooleanField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Length, InputRequired


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
    describe = StringField(label='完成效果', validators=[DataRequired('不能为空')], default='无')
    use_hour = IntegerField(label='消耗小时数', validators=[NumberRange(0, float("inf"), '应为正整数')], default=0)
    use_minute = IntegerField(label='消耗分钟数', validators=[NumberRange(0, float("inf"), '应为正整数'), InputRequired('不能为空')])
    submit = SubmitField(label='确定')
    

class LoginForm(FlaskForm):
    """
    登录表单
    - 注：暂时复用为注册表单，后期可能要改"""
    username = StringField(label='用户名', validators=[DataRequired('不能为空')])
    password = PasswordField(label='密码', validators=[DataRequired('不能为空')])
    remenber = BooleanField(label='记住我', default=False)
    submit = SubmitField(label='确定')

class UserForm(FlaskForm):
    """修改个人基本信息"""
    username = StringField(label='用户名', validators=[DataRequired('不能为空')])
    email = StringField(label='邮箱', validators=[DataRequired('不能为空'), Length(max=64, message="输入长度不能超过64")])
    introduce = StringField(label='个人简介', validators=[DataRequired('不能为空'), Length(max=128, message="输入长度不能超过128")])
    submit = SubmitField(label='确定')

class UploadForm(FlaskForm):
    photo = FileField('上传图片', validators=[FileRequired(), FileAllowed(['jpg','jpeg','png','gif'])])
    submit = SubmitField(label='确定')

class UpJsonForm(FlaskForm):
    file = FileField('上传.json用户数据文件', validators=[FileRequired(), FileAllowed(['json'])])
    submit = SubmitField(label='确定')

class BookForm(FlaskForm):
    """书籍创建/修改表单"""
    bookname = StringField(label='书名', validators=[DataRequired('不能为空')])
    page = IntegerField(label='总页数', validators=[NumberRange(0, float("inf"), '应为正整数'), DataRequired('不能为空')])
    taskname = StringField(label='绑定的任务名', default='?') # 到时候应该根据已有任务给选项？
    c_task = BooleanField(label='创建相应任务', default=True)
    submit = SubmitField(label='确定')
   
class PlanForm(FlaskForm):
    '''@attributes: name, need_minute, submit'''
    name = StringField(label='计划名称', validators=[DataRequired('不能为空')])
    need_minute = IntegerField(label='计划用时(m)', validators=[NumberRange(0, float("inf"), '应为正整数')], default=600)
    taskname = StringField(label='绑定的任务名', default='?') 
    submit = SubmitField(label='确定')
