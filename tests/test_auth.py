import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException

from api import auth


def test_missing_bearer_token_is_rejected(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.require_authenticated_user(None))

    assert error.value.status_code == 401


def test_supabase_validates_bearer_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co/")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "user-123", "email": "user@example.com"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers):
            assert url == "https://project.supabase.co/auth/v1/user"
            assert headers == {
                "apikey": "public-key",
                "Authorization": "Bearer access-token",
            }
            return FakeResponse()

    monkeypatch.setattr(auth.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    user = asyncio.run(auth.require_authenticated_user("Bearer access-token"))

    assert user["id"] == "user-123"


def test_invalid_supabase_token_is_rejected(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")

    class FakeResponse:
        status_code = 401

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers):
            return FakeResponse()

    monkeypatch.setattr(auth.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.require_authenticated_user("Bearer expired-token"))

    assert error.value.status_code == 401


def test_research_endpoint_requires_auth_but_health_check_is_public(monkeypatch):
    from api.app import app

    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")

    async def call_api():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            protected = await client.post(
                "/research/stream",
                json={"topic": "A sufficiently long research question"},
            )
            health = await client.get("/")
            return protected, health

    protected, health = asyncio.run(call_api())

    assert protected.status_code == 401
    assert health.status_code == 200


def test_streamlit_auth_screen_offers_all_sign_in_methods(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")
    script = Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py"

    app = AppTest.from_file(str(script), default_timeout=20).run()

    assert not app.exception
    assert [element.value for element in app.title] == ["Sign in to M.A.R.S."]
    button_labels = {element.label for element in app.button}
    assert {
        "Continue with Google",
        "Continue with GitHub",
        "Sign in",
        "Create account",
    } <= button_labels


def test_missing_supabase_settings_show_local_setup_instructions(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")
    script = Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py"

    app = AppTest.from_file(str(script), default_timeout=20).run()

    assert not app.exception
    assert any("SUPABASE_URL" in element.value for element in app.error)
    assert any(
        "SUPABASE_REDIRECT_URL=https://fact-checker-agent-hgqyvxqwdxnaz6b5yjg8x2.streamlit.app/" in element.value
        for element in app.code
    )
