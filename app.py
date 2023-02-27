from app import create_app, db
import argparse
import os


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--init_db", help="Initialise the db if it not exist", action="store_true")
parser.add_argument("-r", "--recreate_db", help="Delete and initialise the db", action="store_true")
parser.add_argument("-d", "--delete_db", help="Delete and initialise the db", action="store_true")
args = parser.parse_args()

app = create_app()

if args.init_db:
    with app.app_context():
        db.create_all()
        
elif args.recreate_db:
    with app.app_context():
        db.drop_all()
        db.create_all()
elif args.delete_db:
    with app.app_context():
        db.drop_all()
else:
    app.run(host=app.config.get("FLASK_URL"), port=app.config.get("FLASK_PORT"))