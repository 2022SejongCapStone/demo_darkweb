from flask import render_template, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from flask.globals import request
from .. import db
from . import auth
from .forms import SignupForm, LoginForm
from ..models import User
from sqlalchemy import exc
import os

@auth.route('/signup/', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User(email=form.email.data,
                username=form.username.data,
                password=form.password.data)
            try:    
                db.session.add(user)
                db.session.commit()
                if not os.path.exists('./uploads/' + form.email.data):
                    os.makedirs('./uploads/' + form.email.data)
                flash('가입되었습니다. 로그인 하세요.')                
                return redirect(url_for('main.index'))
            except exc.IntegrityError:
                db.session.rollback()
                flash('사용중인 이메일 주소입니다.')
        else:
            flash('이미 등록된 사용자입니다.')
    return render_template('auth/signup.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm() 
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('이메일 또는 비밀번호를 확인하세요.') 
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('main.index'))  

# 방문할 때마다 최근 방문시간을 갱신한다.
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
