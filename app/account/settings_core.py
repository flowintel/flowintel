"""Per-user settings (UserSettings): interface theme and font for now."""
from ..db_class.db import UserSettings
from ..extensions import db

DEFAULTS = {"theme": "auto", "font": "rubik"}


def get_settings(user):
    """Settings of a user, or an unsaved row with the defaults when they never changed anything."""
    if not user or not getattr(user, "is_authenticated", False):
        return UserSettings(**DEFAULTS)
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    return settings or UserSettings(user_id=user.id, **DEFAULTS)


def get_theme(user):
    return get_settings(user).theme or DEFAULTS["theme"]


def get_font(user):
    return get_settings(user).font or DEFAULTS["font"]


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
