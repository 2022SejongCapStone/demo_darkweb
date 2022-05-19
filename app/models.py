from . import db
from . import login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask.globals import request
from flask_login import UserMixin, AnonymousUserMixin
from markdown import markdown
from datetime import datetime
import bleach
import hashlib

class Permission:
    COMMENT = 1
    WRITE = 2
    CLEAN = 4
    ADMIN = 8
    FILE = 16

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    # 여러 사용자가 같은 Role을 가질 수 있다.
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.COMMENT, Permission.WRITE, Permission.FILE],
            'Cleaner': [Permission.COMMENT, Permission.WRITE, Permission.CLEAN],
            'Administrator': [Permission.COMMENT, Permission.WRITE, Permission.CLEAN, Permission.ADMIN, Permission.FILE],
        }

        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()    

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0   

    def __repr__(self):
        return '<Role %r>' % self.name

post_recommend = db.Table(
    'post_recommend',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('timestamp', db.DateTime, default=datetime.utcnow)
)

reply_recommend = db.Table(
    'reply_recommend',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('reply_id', db.Integer, db.ForeignKey('replies.id', ondelete='CASCADE'), primary_key=True),
    db.Column('timestamp', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))

    # 회원은 Role를 가진다.
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    # ---- 프로필 ----
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))

    # 작성한 글 리스트 
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    replies = db.relationship('Reply', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['DARKWEB_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
            if self.email is not None and self.avatar_hash is None:
                self.avatar_hash = self.gravatar_hash()

    @property 
    def password(self):
        raise AttributeError('비밀번호는 읽을 수 없습니다.')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    # 가장 최근 방문한 시간
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    # Gravatar
    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

# 로그인 여부 확인하지 않고도 can, is_administrator를 사용할 수 있음
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))     

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    filepath = db.Column(db.String(100))
    # 작성자 
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    like = db.relationship('User', secondary=post_recommend, backref='like_posts')

    replies = db.relationship('Reply', backref='post')
    comments = db.relationship('Comment', backref='post')

    @staticmethod
    def on_change_body(target, value, oldValue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'br']
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

db.event.listen(Post.body, 'set', Post.on_change_body)

class Reply(db.Model):
    __tablename__ = 'replies'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # 답글 작성자
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))  

    # 이 답글의 게시글
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    like = db.relationship('User', secondary=reply_recommend, backref='like_replies')

    comments = db.relationship('Comment', backref='reply')

    @staticmethod
    def on_change_body(target, value, oldValue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'br']
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

db.event.listen(Reply.body, 'set', Reply.on_change_body)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)

    # 코멘트 작성자
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 게시글 코멘트
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    # 답글 코멘트
    reply_id = db.Column(db.Integer, db.ForeignKey('replies.id'))