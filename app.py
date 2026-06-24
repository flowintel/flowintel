import argparse
import os
import json
import logging
from logging.handlers import RotatingFileHandler

from flask import flash, jsonify, redirect, render_template, request, Response, send_from_directory, url_for

from app.extensions import db
from app import create_app

from app.utils.init_db import create_admin
from app.utils.init_taxonomies import create_taxonomies, create_galaxies
from app.utils.utils import get_modules_list, update_pymisp_objects
from app.utils.init_misp_modules import create_modules_db

from conf.config import Config


#######
# Log #
#######
logs_folder = os.path.join(os.getcwd(), "logs")
if not os.path.isdir(logs_folder):
    os.mkdir(logs_folder)
rootLogger = logging.getLogger()

# Log formatter, timestamp in Flask format
log_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%d/%b/%Y %H:%M:%S')

log_file = Config.LOG_FILE if hasattr(Config, 'LOG_FILE') else 'record.log'
my_handler = RotatingFileHandler(f"{logs_folder}/{log_file}", mode='a', maxBytes=10*1024*1024, 
                                 backupCount=5, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)

rootLogger.addHandler(my_handler)
# fileHandler = logging.FileHandler('logs/record.log')
# rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(log_formatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.DEBUG)


############
# ArgParse #
############
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--init_db", help="Initialise the db if it not exist", action="store_true")
parser.add_argument("-r", "--recreate_db", help="Delete and initialise the db", action="store_true")
parser.add_argument("-d", "--delete_db", help="Delete the db", action="store_true")
parser.add_argument("-tg", "--taxo_galaxies", help="Add taxonomies and galaxies", action="store_true")
parser.add_argument("-utg", "--update_taxo_galaxies", help="Update taxonomies and galaxies", action="store_true")
parser.add_argument("-mm", "--misp_modules", help="Add or update misp-modules", action="store_true")
parser.add_argument("-py", "--pymisp", help="Update pymisp misp objects", action="store_true")
parser.add_argument("-td", "--test_data", help="Create default test cases", action="store_true")
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
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({"error": "CSRF token expired", "csrf_token": True}), 400
    flash("Your session has expired. Please try again.", "warning")
    return redirect(request.referrer or url_for('account.login'))

@app.route('/favicon.ico') 
def favicon(): 
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    
if args.init_db:
    with app.app_context():
        from alembic.config import Config
        from alembic import command

        cfg = Config("migrations/alembic.ini")

        # Kept in case we need to revert to branching
        # from app.db_utils import get_engine
        # if get_engine().dialect.name in ("mysql", "mariadb"):
        #     # MariaDB branch contains a properly created "full" alembic init migration
        #     command.upgrade(cfg, "mariadb@head")
        # else:
        #     db.create_all()
        #     command.stamp(cfg, "postgres@head")
        #     # Kept for legacy - how to recreate the init migrations script by replacing the previous 2 lines with:
        #     # The app will badly crash, but you will generated the file that can be docker copied out
        #     # command.revision(cfg, message="Initial migration", autogenerate=True)
        #     # command.upgrade(cfg, "postgres@head")
        #     #
        db.create_all()
        command.stamp(cfg, "head")
        create_admin()
elif args.recreate_db:
    with app.app_context():
        db.drop_all()
        from alembic.config import Config
        from alembic import command

        cfg = Config("migrations/alembic.ini")

        # Kept in case we need to revert to branching
        # from app.db_utils import get_engine
        # if get_engine().dialect.name in ("mysql", "mariadb"):
        #     command.upgrade(cfg, "mariadb@head")
        # else:
        #     db.create_all()
        #     command.stamp(cfg, "postgres@head")
        db.create_all()
        command.stamp(cfg, "head")
        create_admin()
elif args.delete_db:
    with app.app_context():
        db.drop_all()
elif args.taxo_galaxies:
    with app.app_context():
        create_taxonomies(True)
        create_galaxies(True)
elif args.update_taxo_galaxies:
    with app.app_context():
        create_taxonomies(False)
        create_galaxies(False)
elif args.misp_modules:
    with app.app_context():
        create_modules_db()
elif args.pymisp:
    with app.app_context():
        update_pymisp_objects()
elif args.test_data:
    with app.app_context():
        from app.db_class.db import User
        from app.utils.init_db import create_default_case
        admin_user = User.query.filter_by(role_id=1).first()
        if admin_user:
            create_default_case(admin_user)
        else:
            print("Error: No admin user found")

else:
    # get_modules_list()
    app.run(host=app.config.get("FLASK_URL"), port=app.config.get("FLASK_PORT"))
