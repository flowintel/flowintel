from .. import db
from ..db_class.db import User

def add_user_core(form):
    user = User(
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        email=form.email.data,
        password=form.password.data)
    db.session.add(user)
    db.session.commit()