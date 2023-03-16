from .. import db
from ..db_class.db import User
import bleach
from ..utils.utils import generate_api_key

def add_user_core(form):
    user = User(
        first_name=bleach.clean(form.first_name.data),
        last_name=bleach.clean(form.last_name.data),
        email=bleach.clean(form.email.data),
        password=bleach.clean(form.password.data),
        role = "user",
        api_key = generate_api_key()
    )
    db.session.add(user)
    db.session.commit()