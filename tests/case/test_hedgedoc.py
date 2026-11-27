from unittest.mock import Mock

import pytest
import requests
from flask.sessions import SecureCookieSessionInterface

from app.db_class.db import Case, User
from app.extensions import db


BASE_URL = "https://notes.example.test:8443/pad"
NOTE_URL = f"{BASE_URL}/incident-42"
EDITOR = {"X-API-KEY": "editor_api_key"}


@pytest.fixture
def editor_case(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "HEDGEDOC_BASE_URL", BASE_URL)
    monkeypatch.setattr(app, "session_interface", SecureCookieSessionInterface())
    response = client.post("/api/case/create", headers=EDITOR, json={"title": "Notes"})
    assert response.status_code == 201
    with app.app_context():
        login_id = User.query.filter_by(api_key=EDITOR["X-API-KEY"]).one().get_id()
    with client.session_transaction() as session:
        session["_user_id"] = login_id
        session["_fresh"] = True
    return response.json["case_id"]


@pytest.fixture
def http_get(monkeypatch):
    get = Mock(return_value=Mock(status_code=200, text="# Case notes"))
    monkeypatch.setattr(requests, "get", get)
    return get


def store_existing_url(app, cid, url):
    # Seed the row directly to represent data saved before URL validation.
    with app.app_context():
        db.session.get(Case, cid).hedgedoc_url = url
        db.session.commit()


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/note",
    "https://other.example.test:8443/pad/note",
    "http://notes.example.test:8443/pad/note",
    "https://notes.example.test/pad/note",
    "https://user@notes.example.test:8443/pad/note",
    f"{BASE_URL}/../note",
    f"{BASE_URL}/%2e%2e",
])
def test_existing_untrusted_url_is_never_fetched(app, client, editor_case, http_get, url):
    store_existing_url(app, editor_case, url)
    response = client.get(f"/case/{editor_case}/get_hedgedoc_notes")
    assert response.status_code == 400
    assert "notes" not in response.json
    http_get.assert_not_called()


def test_existing_note_uses_current_configuration(app, client, editor_case, http_get):
    store_existing_url(app, editor_case, NOTE_URL)
    endpoint = f"/case/{editor_case}/get_hedgedoc_notes"
    assert client.get(endpoint).json == {"notes": "# Case notes"}
    http_get.assert_called_once_with(f"{NOTE_URL}/download", timeout=(3, 10), allow_redirects=False)

    app.config.pop("HEDGEDOC_BASE_URL")
    assert client.get(endpoint).status_code == 400
    assert http_get.call_count == 1
    response = client.post(f"/case/{editor_case}/change_hedgedoc_url", json={"hedgedoc_url": ""})
    assert response.status_code == 200
    assert client.get(endpoint).json == {"notes": ""}
    assert http_get.call_count == 1


def test_existing_blank_url_returns_empty_notes(app, client, editor_case, http_get):
    store_existing_url(app, editor_case, "  ")
    assert client.get(f"/case/{editor_case}/get_hedgedoc_notes").json == {"notes": ""}
    http_get.assert_not_called()


def test_existing_note_matches_effective_port(app, client, editor_case, http_get):
    app.config["HEDGEDOC_BASE_URL"] = "https://notes.example.test/"
    endpoint = f"/case/{editor_case}/get_hedgedoc_notes"
    store_existing_url(app, editor_case, "https://notes.example.test:0/note")
    assert client.get(endpoint).status_code == 400
    http_get.assert_not_called()

    store_existing_url(app, editor_case, "https://NOTES.example.test:443/note")
    assert client.get(endpoint).json == {"notes": "# Case notes"}
    http_get.assert_called_once_with("https://notes.example.test/note/download", timeout=(3, 10), allow_redirects=False)


def test_download_refuses_redirect(app, client, editor_case, monkeypatch):
    store_existing_url(app, editor_case, NOTE_URL)

    def redirect_response(request, **kwargs):
        redirect = requests.Response()
        redirect.request = request
        redirect.url = request.url
        redirect.status_code = 302
        redirect.headers["Location"] = "https://other.example.test/"
        redirect._content = b""
        return redirect

    send = Mock(side_effect=redirect_response)
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    response = client.get(f"/case/{editor_case}/get_hedgedoc_notes")
    assert response.status_code == 404
    assert "notes" not in response.json
    send.assert_called_once()
    assert send.call_args.args[0].url == f"{NOTE_URL}/download"


def test_create_and_update_validate_before_saving(app, client, editor_case, http_get):
    invalid = "https://other.example.test/note"
    create = client.post("/api/case/create", headers=EDITOR, json={"title": "Invalid", "hedgedoc_url": invalid})
    assert create.status_code == 400
    create = client.post("/api/case/create", headers=EDITOR, json={"title": "Valid", "hedgedoc_url": NOTE_URL + "?edit"})
    assert create.status_code == 201

    endpoint = f"/case/{editor_case}/change_hedgedoc_url"
    assert client.post(endpoint, json={"hedgedoc_url": NOTE_URL + "?both#"}).status_code == 200
    assert client.post(endpoint, json={"hedgedoc_url": invalid}).status_code == 400
    with app.app_context():
        assert Case.query.filter_by(title="Invalid").first() is None
        assert db.session.get(Case, create.json["case_id"]).hedgedoc_url == NOTE_URL
        assert db.session.get(Case, editor_case).hedgedoc_url == NOTE_URL
    http_get.assert_not_called()
