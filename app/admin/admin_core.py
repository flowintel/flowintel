from .. import db
from ..db_class.db import User
import bleach

def add_user_core(form):
    user = User(
        first_name=bleach.clean(form.first_name.data),
        last_name=bleach.clean(form.last_name.data),
        email=bleach.clean(form.email.data),
        password=bleach.clean(form.password.data),
        role = "user"
    )
    db.session.add(user)
    db.session.commit()