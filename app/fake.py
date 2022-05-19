from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from app.models import User, Post

def users(count=100):
    fake = Faker('ko_KR')
    i = 0
    while i < count:
        u = User(email=fake.email(),
                username=fake.user_name(),
                password='password')
        db.session.add(u)
        # 사용자 중복 등록이 되지 않는다.
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()

def posts(count=100):
    fake = Faker('ko_KR')
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(subject=fake.text(),
                body=fake.text(),
                timestamp=fake.past_date(),
                author=u)
        db.session.add(p)
        db.session.commit()