#!/usr/bin/env python3
from app import create_app
from app.db_class.db import User
from app.utils.init_db import create_default_case

app = create_app()

with app.app_context():
    user = User.query.filter_by(role_id=1).first()
    if not user:
        print("Error: No admin user found")
        exit(1)
    
    create_default_case(user)
    print("Test data created")
