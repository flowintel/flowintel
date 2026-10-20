import pytest
import redis
from flask import Flask

from app import configure_valkey_session, session


@pytest.fixture
def simulate_redis(monkeypatch):
    captured = {}

    class FakeRedis:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(redis, "Redis", FakeRedis)
    monkeypatch.setattr(session, "init_app", lambda *a, **k: None)
    return captured


def simulate_app(**overrides):
    app = Flask(__name__)
    app.config.update(VALKEY_IP="valkey", VALKEY_PORT="6379",
                      VALKEY_USERNAME=None, VALKEY_PASSWORD=None)
    app.config.update(overrides)
    return app


@pytest.mark.parametrize("port", ["abc", "", None, "0", "70000"])
def test_invalid_port_raises(simulate_redis, port):
    with pytest.raises(RuntimeError, match="Invalid VALKEY_PORT"):
        configure_valkey_session(simulate_app(VALKEY_PORT=port))


@pytest.mark.parametrize("host", ["", None, " "])
def test_missing_host_raises(simulate_redis, host):
    with pytest.raises(RuntimeError, match="VALKEY_IP"):
        configure_valkey_session(simulate_app(VALKEY_IP=host))


@pytest.mark.parametrize("valkey_ip", ["valkey", "127.0.0.1", "::1", "mycache-server.vps.com"])
def test_credentials_forwarded_unencoded(simulate_redis, valkey_ip):
    configure_valkey_session(
        simulate_app(
            VALKEY_IP=valkey_ip,
            VALKEY_USERNAME="flowintel",
            VALKEY_PASSWORD="p@ss:w/rd",
        ))
    assert simulate_redis["host"] == valkey_ip
    assert simulate_redis["port"] == 6379
    assert simulate_redis["username"] == "flowintel"
    assert simulate_redis["password"] == "p@ss:w/rd"


def test_no_auth_when_unset(simulate_redis):
    configure_valkey_session(simulate_app())
    assert simulate_redis["username"] is None and simulate_redis["password"] is None


def test_username_without_password_dropped(simulate_redis, caplog):
    app = simulate_app(VALKEY_USERNAME="flowintel")
    with caplog.at_level("WARNING"):
        configure_valkey_session(app)
    assert simulate_redis["username"] is None
    assert "ignoring VALKEY_USERNAME" in caplog.text


def test_session_redis_is_set_and_session_initialised(simulate_redis, monkeypatch):
    calls = []
    monkeypatch.setattr(session, "init_app", lambda app: calls.append(app))
    app = simulate_app(VALKEY_PASSWORD="s3cret")
    configure_valkey_session(app)
    assert app.config["SESSION_REDIS"] is not None
    assert calls == [app]


@pytest.mark.parametrize("user, password, exp_user, exp_password", [
    ("flowintel", "p@ss:w/rd", "flowintel", "p@ss:w/rd"),
    (None, "s3cret", None, "s3cret"),
    ("", "s3cret", None, "s3cret"),
    ("", "", None, None),
])
def test_auth_matrix(simulate_redis, user, password, exp_user, exp_password):
    configure_valkey_session(simulate_app(VALKEY_USERNAME=user, VALKEY_PASSWORD=password))
    assert simulate_redis["username"] == exp_user
    assert simulate_redis["password"] == exp_password


def test_password_never_logged(simulate_redis, caplog):
    with caplog.at_level("DEBUG"):
        configure_valkey_session(simulate_app(VALKEY_PASSWORD="s3cret-do-not-log"))
    assert "s3cret-do-not-log" not in caplog.text


def test_timeouts_are_set(simulate_redis):
    configure_valkey_session(simulate_app())
    assert simulate_redis["socket_connect_timeout"] == 3
    assert simulate_redis["socket_timeout"] == 3
