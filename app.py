from app import create_app, db
import argparse
from app.utils.init_db import create_admin
from flask import render_template, request, Response
import json


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--init_db", help="Initialise the db if it not exist", action="store_true")
parser.add_argument("-r", "--recreate_db", help="Delete and initialise the db", action="store_true")
parser.add_argument("-d", "--delete_db", help="Delete and initialise the db", action="store_true")
args = parser.parse_args()

app = create_app()

@app.errorhandler(404)
def error_page_not_found(e):
    if request.path.startswith('/api/'):
        return Response(json.dumps({"status": "error", "reason": "404 Not Found"}, indent=2, sort_keys=True), mimetype='application/json'), 404
    return render_template('404.html'), 404
    

if args.init_db:
    with app.app_context():
        db.create_all()
        create_admin()
        
elif args.recreate_db:
    with app.app_context():
        db.drop_all()
        db.create_all()
        create_admin()
elif args.delete_db:
    with app.app_context():
        db.drop_all()
else:
    app.run(host=app.config.get("FLASK_URL"), port=app.config.get("FLASK_PORT"))