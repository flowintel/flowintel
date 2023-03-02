from .. import db
from ..db_class.db import User

def create_user():
    user = User(
        first_name="David",
        last_name="Cruciani",
        email="admin@admin.com",
        password="admin")
    db.session.add(user)
    db.session.commit()