import datetime
import logging

import gnupg
from flask import current_app

log = logging.getLogger(__name__)


def gpg_enabled():
    """Return True if GPG signing is configured."""
    return bool(current_app.config.get("GPG_KEY_ID"))


def sign_text(content):
    """Create a detached ASCII-armoured GPG signature for *content*."""
    if not gpg_enabled():
        return None

    home = current_app.config.get("GPG_HOME") or None
    key_id = current_app.config["GPG_KEY_ID"]
    passphrase = current_app.config.get("GPG_PASSPHRASE") or None

    gpg = gnupg.GPG(gnupghome=home)
    sig = gpg.sign(content.encode("utf-8"), keyid=key_id, detach=True, passphrase=passphrase)

    if not sig or not sig.data:
        log.error("GPG signing failed: %s", sig.stderr)
        return {"error": f"GPG signing failed: {sig.stderr}"}

    return {
        "signature": str(sig),
        "signed_by": key_id,
        "signed_at": datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
