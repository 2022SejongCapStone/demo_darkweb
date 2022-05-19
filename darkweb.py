import os
from app import create_app, db
from app.models import User, Role

app = create_app(os.getenv('DARKWEB_CONFIG') or 'default')

# flask shell 명령어에 자동으로 제공함
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)