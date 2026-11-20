"""Global search of the top bar (see search_core.py)."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from . import search_core as SearchModel

search_blueprint = Blueprint('search', __name__)


@search_blueprint.route("/quick", methods=['GET'])
@login_required
def quick():
    """Autocomplete results grouped by kind, limited to what the user may see.

    q: the text ("#123" also matches ids); kinds: comma-separated subset of
    cases,tasks,notes,attributes,tags,templates,users,orgs (users/orgs: admins only)."""
    text = request.args.get("q", "", type=str)
    kinds = [k for k in request.args.get("kinds", "", type=str).split(",") if k] or None
    return SearchModel.quick_search(text, current_user, kinds)
