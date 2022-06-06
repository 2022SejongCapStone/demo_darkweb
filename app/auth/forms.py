from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo

class LoginForm(FlaskForm):
    email = StringField('이메일', validators=[DataRequired(), Length(1, 64), Email('이메일 주소가 아닙니다.')])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    remember_me = BooleanField('로그인 상태 유지')
    submit = SubmitField('로그인')

class SignupForm(FlaskForm):        
    email = StringField('이메일', validators=[DataRequired('이메일을 입력하세요.'), Length(1,64), Email('이메일 주소가 아닙니다.')])
    username = StringField('아이디', validators=[DataRequired('아이디를 입력하세요.'), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, '아이디는 문자, 숫자, 점, 밑줄만 사용할 수 있습니다.')])
    password = PasswordField('비밀번호', validators=[DataRequired('비밀번호를 입력하세요.'), EqualTo('password2', message='비밀번호가 일치하지 않습니다.')])
    password2 = PasswordField('비밀번호 확인', validators=[DataRequired('비밀번호 확인을 입력하세요.')])
    submit = SubmitField('회원등록')