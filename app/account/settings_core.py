"""Per-user settings (UserSettings): interface theme, font and default case list display."""
from ..db_class.db import UserSettings
from ..extensions import db
from ..utils.themes import THEMES

DEFAULTS = {"theme": "auto", "font": "rubik", "case_view": "cards", "tag_view": "compact", "sticky_header": "scroll"}


def get_settings(user):
    """Settings of a user, or an unsaved row with the defaults when they never changed anything."""
    if not user or not getattr(user, "is_authenticated", False):
        return UserSettings(**DEFAULTS)
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    return settings or UserSettings(user_id=user.id, **DEFAULTS)


def get_theme(user):
    """Saved theme, or the default one when it is unset or no longer exists."""
    theme = get_settings(user).theme
    return theme if theme in THEMES else DEFAULTS["theme"]


def get_font(user):
    return get_settings(user).font or DEFAULTS["font"]


def get_case_view(user):
    """Default display of the case index: "table" or "cards"."""
    view = get_settings(user).case_view
    return view if view in UserSettings.CHOICES["case_view"] else DEFAULTS["case_view"]


def get_tag_view(user):
    """Default look of the tags in the case view: "compact" or "context"."""
    view = get_settings(user).tag_view
    return view if view in UserSettings.CHOICES["tag_view"] else DEFAULTS["tag_view"]


def get_sticky_header(user):
    """Top bar behaviour: "scroll" (goes away with the page) or "fixed" (stays at the top)."""
    value = get_settings(user).sticky_header
    return value if value in UserSettings.CHOICES["sticky_header"] else DEFAULTS["sticky_header"]


def update_settings(user, changes):
    """Apply {field: value} changes. Returns (settings, None) or (None, error message).

    Only fields listed in UserSettings.CHOICES are accepted, with one of their values;
    nothing is saved when any change is invalid.
    """
    if not isinstance(changes, dict) or not changes:
        return None, "Nothing to update"
    for field, value in changes.items():
        if field not in UserSettings.CHOICES:
            return None, f"Unknown setting '{field}'"
        if value not in UserSettings.CHOICES[field]:
            return None, f"Invalid value for '{field}'"

    settings = UserSettings.query.filter_by(user_id=user.id).first()
    if not settings:
        settings = UserSettings(user_id=user.id, **DEFAULTS)
        db.session.add(settings)
    for field, value in changes.items():
        setattr(settings, field, value)
    db.session.commit()
    return settings, None
