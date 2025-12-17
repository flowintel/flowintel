from app import create_app, db
import argparse
from app.utils.init_db import create_admin
from app.utils.init_taxonomies import create_taxonomies, create_galaxies
from app.utils.utils import get_modules_list, update_pymisp_objects
from app.utils.init_misp_modules import create_modules_db
from flask import jsonify, render_template, request, Response, send_from_directory
import json

import os
import logging
from logging.handlers import RotatingFileHandler
from conf.config import Config

#######
# Log #
#######
logs_folder = os.path.join(os.getcwd(), "logs")
if not os.path.isdir(logs_folder):
    os.mkdir(logs_folder)
rootLogger = logging.getLogger()

log_file = Config.LOG_FILE if hasattr(Config, 'LOG_FILE') else 'record.log'
my_handler = RotatingFileHandler(f"{logs_folder}/{log_file}", mode='a', maxBytes=10*1024*1024, 
                                 backupCount=5, encoding=None, delay=0)

rootLogger.addHandler(my_handler)
# fileHandler = logging.FileHandler('logs/record.log')
# rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.DEBUG)


############
# ArgParse #
############
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--init_db", help="Initialise the db if it not exist", action="store_true")
parser.add_argument("-r", "--recreate_db", help="Delete and initialise the db", action="store_true")
parser.add_argument("-d", "--delete_db", help="Delete the db", action="store_true")
parser.add_argument("-tg", "--taxo_galaxies", help="Add or update taxonomies and galaxies", action="store_true")
parser.add_argument("-mm", "--misp_modules", help="Add or update misp-modules", action="store_true")
parser.add_argument("-py", "--pymisp", help="Update pymisp misp objects", action="store_true")
args = parser.parse_args()

app = create_app()

@app.errorhandler(404)
def error_page_not_found(e):
    if request.path.startswith('/api/'):
        return Response(json.dumps({"status": "error", "reason": "404 Not Found"}, indent=2, sort_keys=True), mimetype='application/json'), 404
    return render_template('404.html'), 404

from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    response = {"error": "CSRF token expired", "csrf_token": True}
    return jsonify(response), 400  # Code 400 pour erreur côté client

@app.route('/favicon.ico') 
def favicon(): 
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    

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
elif args.taxo_galaxies:
    with app.app_context():
        create_taxonomies(True)
        create_galaxies(True)
elif args.misp_modules:
    with app.app_context():
        create_modules_db()
elif args.pymisp:
    with app.app_context():
        update_pymisp_objects()
else:
    # get_modules_list()
    app.run(host=app.config.get("FLASK_URL"), port=app.config.get("FLASK_PORT"))