from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, FileField
from wtforms.validators import DataRequired, Length, Email, Regexp
from flask_pagedown.fields import PageDownField
from wtforms import ValidationError
from ..models import Role, User

# 회원 자신 프로필 수정
class EditProfileForm(FlaskForm):
    name = StringField('이름', validators=[Length(0, 64)])
    location = StringField('사는 곳', validators=[Length(0, 64)])
    about_me = TextAreaField('나는 ')
    submit = SubmitField('저장')

# 관리자의 회원 프로필 수정
class EditProfileAdminForm(FlaskForm):
    email = StringField('이메일', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('아이디', validators=[DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, '아이디는 문자, 숫자, 점, 밑줄만 사용할 수 있습니다.')])
    role = SelectField('역할', coerce=int)

    name = StringField('이름', validators=[Length(0, 64)])
    location = StringField('사는 곳', validators=[Length(0, 64)])
    about_me = TextAreaField('나는 ')
    submit = SubmitField('저장')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('사용중인 이메일입니다.')

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('사용중인 아이디입니다.')

# 글쓰기 폼
class PostForm(FlaskForm):
    subject = StringField('제목', validators=[DataRequired('제목을 입력하세요.')])
    body = PageDownField('내용', render_kw={"rows":5 }, validators=[DataRequired('내용을 입력하세요.')])
    upload = FileField('파일 업로드')
    submit = SubmitField('글쓰기')

# 답글쓰기 폼
class PostReplyForm(FlaskForm):
    body = PageDownField('답글쓰기', render_kw={"rows":5 }, validators=[DataRequired('답글을 입력하세요.')])
    submit = SubmitField('답글쓰기')

class CommentForm(FlaskForm):
    body = TextAreaField('내용', validators=[DataRequired('내용을 입력하세요.')])
    submit = SubmitField('댓글쓰기')