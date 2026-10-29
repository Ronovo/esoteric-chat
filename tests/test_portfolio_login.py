import base64
import time
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from esoteric_chat.server import create_app


@pytest.fixture
def issue(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    monkeypatch.setenv("PORTFOLIO_SSO_URL", "http://portfolio.test")
    monkeypatch.setenv("PORTFOLIO_SSO_PUBLIC_KEY", base64.b64encode(public).decode())

    def issue(aud="esoteric-chat", sub="1", name="ronovo", expires_in=300):
        now = int(time.time())
        claims = {"iss": "portfolio", "aud": aud, "sub": sub, "name": name, "iat": now, "exp": now + expires_in}
        return jwt.encode(claims, key, algorithm="RS256")
    return issue


def start_login(client):
    res = client.get("/sso/login")
    assert res.status_code == 302
    query = parse_qs(urlsplit(res.location).query)
    assert query["app"] == ["esoteric-chat"]
    assert query["return"] == ["http://localhost/sso/callback"]
    return query["state"][0]


def test_portfolio_login_is_off_without_config(monkeypatch):
    monkeypatch.delenv("PORTFOLIO_SSO_URL", raising=False)
    monkeypatch.delenv("PORTFOLIO_SSO_PUBLIC_KEY", raising=False)
    client = create_app().test_client()
    assert b"Log in with portfolio account" not in client.get("/").data
    assert client.get("/sso/login").status_code == 404


def test_portfolio_login_and_logout(issue):
    client = create_app().test_client()
    assert b"Log in with portfolio account" in client.get("/").data
    state = start_login(client)
    assert client.post("/sso/callback", data={"state": state, "token": issue()}).status_code == 302
    assert b"Logged in as ronovo" in client.get("/").data
    client.post("/logout")
    assert b"Logged in as" not in client.get("/").data


@pytest.mark.parametrize("bad", [
    {"state": "wrong"},
    {"aud": "casino"},
    {"expires_in": -10},
])
def test_portfolio_login_rejects_bad_callbacks(issue, bad):
    client = create_app().test_client()
    state = start_login(client)
    token = issue(aud=bad.get("aud", "esoteric-chat"), expires_in=bad.get("expires_in", 300))
    res = client.post("/sso/callback", data={"state": bad.get("state", state), "token": token})
    assert res.status_code == 400
    assert b"Logged in as" not in client.get("/").data
