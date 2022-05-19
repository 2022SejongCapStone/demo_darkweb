from flask import Flask  
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_moment import Moment
from flask_login import LoginManager
from flask_pagedown import PageDown
from config import config

naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()
moment = Moment()
pagedown = PageDown()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_name):  
    app = Flask(__name__)  

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith("sqlite"):
        migrate.init_app(app, db, render_as_batch=True)
    else:
        migrate.init_app(app, db)

    moment.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import main as main_bp
    app.register_blueprint(main_bp)

    # 템플릿 필터 직접 만들기
    from .filter import format_datetime, format_date
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['date'] = format_date

    return app