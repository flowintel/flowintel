from .. import db
from ..db_class.db import User
from .utils import generate_api_key

def create_user():
    user = User(
        first_name="David",
        last_name="Cruciani",
        email="admin@admin.com",
        password="admin",
        role='admin',
        api_key = generate_api_key()
    )
    db.session.add(user)
    db.session.commit()