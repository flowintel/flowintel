"""Shared TLS verification settings for MISP and mail clients."""

import ssl

import conf.config_module as Config


def _verify_setting(name):
    value = getattr(Config, name, True)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip():
        return value
    raise ValueError(f"{name} must be True, False, or a nonempty CA bundle path")


def misp_ssl():
    """Return PyMISP's verification option, reading configuration at call time."""
    return _verify_setting("MISP_VERIFY_SSL")


def mail_ssl_context():
    """Build the certificate and hostname verification context for IMAP/SMTP."""
    verify = _verify_setting("MAIL_VERIFY_SSL")
    context = ssl.create_default_context(cafile=verify if isinstance(verify, str) else None)
    if verify is False:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context
