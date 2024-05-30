from .. import db
from ..db_class.db import *


def get_analyzer(analyzer_id):
    """Return an analyzer by id"""
    return Analyzer.query.get(analyzer_id)

def get_analyzers():
    """Return all Analyzers"""
    return Analyzer.query.all()

def change_status_core(analyzer_id):
    """Active or disabled an analyzer"""
    an = get_analyzer(analyzer_id)
    if an:
        an.is_active = not an.is_active
        db.session.commit()
        return True
    return False

def change_config_core(request_json):
    """Change config for an analyzer"""
    analyzer = get_analyzer(request_json["analyzer_id"])
    if analyzer:
        analyzer.name = request_json["analyzer_name"]
        analyzer.url = request_json["analyzer_url"]
        db.session.commit()
        return True
    return False


def add_analyzer_core(form_dict):
    analyzer = Analyzer(
        name=form_dict["name"],
        url = form_dict["url"],
        is_active=True
    )
    db.session.add(analyzer)
    db.session.commit()
    return True

def delete_analyzer(analyzer_id):
    analyzer = get_analyzer(analyzer_id)
    if analyzer:
        db.session.delete(analyzer)
        return True
    return False