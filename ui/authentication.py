"""Streamlit sign-in and account creation using Supabase Auth."""

import os
import time
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv
from supabase_auth import SyncGoTrueClient
from supabase_auth.errors import AuthError
from supabase_auth.types import Session

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "mars_logo.png"

load_dotenv()


def _show_auth_error(exc: Exception) -> None:
    message = getattr(exc, "message", str(exc))
    st.error(f"Authentication failed: {message}")


def _render_oauth_button(
    client: SyncGoTrueClient,
    provider: str,
    redirect_url: str,
) -> None:
    provider_name = "GitHub" if provider == "github" else "Google"
    if not st.button(
        f"Continue with {provider_name}",
        key=f"oauth-{provider}",
        use_container_width=True,
    ):
        return

    try:
        response = client.sign_in_with_oauth(
            {
                "provider": provider,
                "options": {"redirect_to": redirect_url},
            }
        )
    except AuthError as exc:
        _show_auth_error(exc)
        return
    except httpx.RequestError as exc:
        st.error(f"Could not connect to Supabase: {exc}")
        return

    st.session_state["_mars_oauth_redirect"] = {
        "provider": provider,
        "url": response.url,
    }
    st.rerun()


def _render_email_forms(client: SyncGoTrueClient, redirect_url: str) -> None:
    sign_in_tab, create_account_tab = st.tabs(["Sign in", "Create account"])

    with sign_in_tab:
        with st.form("email_sign_in"):
            email = st.text_input("Email", key="sign_in_email", type="default")
            password = st.text_input(
                "Password",
                key="sign_in_password",
                type="password",
            )
            submitted = st.form_submit_button(
                "Sign in",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not email.strip() or not password:
                st.error("Enter your email and password.")
            else:
                try:
                    response = client.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                except AuthError as exc:
                    _show_auth_error(exc)
                except httpx.RequestError as exc:
                    st.error(f"Could not connect to Supabase: {exc}")
                else:
                    if response.session is None:
                        st.info("Check your email to complete account verification.")
                    else:
                        st.rerun()

    with create_account_tab:
        with st.form("email_create_account"):
            email = st.text_input("Email", key="create_account_email", type="default")
            password = st.text_input(
                "Password",
                key="create_account_password",
                type="password",
                help="Use the minimum password length configured in Supabase.",
            )
            submitted = st.form_submit_button(
                "Create account",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not email.strip() or not password:
                st.error("Enter an email and password.")
            else:
                try:
                    response = client.sign_up(
                        {
                            "email": email.strip(),
                            "password": password,
                            "options": {"email_redirect_to": redirect_url},
                        }
                    )
                except AuthError as exc:
                    _show_auth_error(exc)
                except httpx.RequestError as exc:
                    st.error(f"Could not connect to Supabase: {exc}")
                else:
                    if response.session is None:
                        st.success(
                            "Account created. Check your email to confirm your "
                            "address, then sign in."
                        )
                    else:
                        st.rerun()


def _render_sign_in(client: SyncGoTrueClient, redirect_url: str) -> None:
    with st.container(key="auth-card", border=True):
        st.image(str(LOGO_PATH), width=72)
        st.markdown(
            "<div class='eyebrow'>Secure workspace</div>",
            unsafe_allow_html=True,
        )
        st.title("Sign in to M.A.R.S.")
        st.caption("Use your Google, GitHub, or email account.")
        google_column, github_column = st.columns(2)
        with google_column:
            _render_oauth_button(client, "google", redirect_url)
        with github_column:
            _render_oauth_button(client, "github", redirect_url)

        oauth_redirect = st.session_state.get("_mars_oauth_redirect")
        if oauth_redirect:
            provider_name = (
                "GitHub" if oauth_redirect["provider"] == "github" else "Google"
            )
            st.link_button(
                f"Open {provider_name} sign-in",
                oauth_redirect["url"],
                use_container_width=True,
            )

        st.divider()
        _render_email_forms(client, redirect_url)


def authenticate_user() -> tuple[SyncGoTrueClient, Session] | None:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    redirect_url = os.getenv("SUPABASE_REDIRECT_URL", "http://localhost:8501")

    if not supabase_url or not anon_key:
        missing_settings = [
            setting
            for setting, value in (
                ("SUPABASE_URL", supabase_url),
                ("SUPABASE_ANON_KEY", anon_key),
            )
            if not value
        ]
        with st.container(key="auth-setup-card", border=True):
            st.image(str(LOGO_PATH), width=72)
            st.markdown(
                "<div class='eyebrow'>Secure workspace setup</div>",
                unsafe_allow_html=True,
            )
            st.title("M.A.R.S.")
            st.error(
                f"Supabase authentication is not configured: "
                f"{', '.join(missing_settings)}."
            )
            st.markdown(
                "Create a Supabase project, then copy its **Project URL** and "
                "**anon/publishable key** from **Project Settings → API** into "
                "the project-root `.env` file:"
            )
            st.code(
                "SUPABASE_URL=https://<project-ref>.supabase.co\n"
                "SUPABASE_ANON_KEY=<anon-or-publishable-key>\n"
                "SUPABASE_REDIRECT_URL=http://localhost:8501",
                language="dotenv",
            )
            st.markdown(
                "In **Authentication → URL Configuration**, allow "
                "`http://localhost:8501`. In **Authentication → Providers**, "
                "enable Email, Google, and GitHub. Configure OAuth client "
                "credentials in Supabase and use its displayed callback URL in "
                "each provider's settings."
            )
            st.caption(
                "Use the anon/publishable key, never the service-role key. Keep "
                "all project keys in `.env`; do not share them in chat."
            )
            st.link_button(
                "Open Supabase dashboard",
                "https://supabase.com/dashboard",
                use_container_width=True,
            )
        return None

    client = st.session_state.get("_mars_supabase_client")
    if client is None:
        client = SyncGoTrueClient(
            url=f"{supabase_url}/auth/v1",
            headers={
                "apikey": anon_key,
                "Authorization": f"Bearer {anon_key}",
            },
            flow_type="pkce",
        )
        st.session_state["_mars_supabase_client"] = client

    auth_code = st.query_params.get("code")
    if auth_code:
        try:
            response = client.exchange_code_for_session(
                {"auth_code": auth_code}
            )
        except AuthError as exc:
            st.query_params.clear()
            st.session_state.pop("_mars_oauth_redirect", None)
            _show_auth_error(exc)
        except httpx.RequestError as exc:
            st.query_params.clear()
            st.session_state.pop("_mars_oauth_redirect", None)
            st.error(f"Could not complete sign-in with Supabase: {exc}")
        else:
            st.query_params.clear()
            st.session_state.pop("_mars_oauth_redirect", None)
            if response.session is None:
                st.error("Supabase did not return a signed-in session.")
            else:
                st.rerun()

    try:
        session = client.get_session()
        if (
            session is not None
            and session.expires_at is not None
            and session.expires_at <= int(time.time()) + 30
        ):
            session = client.refresh_session(session.refresh_token).session
    except AuthError as exc:
        st.session_state.pop("_mars_supabase_client", None)
        st.warning("Your session expired. Please sign in again.")
        _show_auth_error(exc)
        return None
    except httpx.RequestError as exc:
        st.error(f"Could not refresh your Supabase session: {exc}")
        return None

    if session is not None:
        return client, session

    _render_sign_in(client, redirect_url)
    return None


def sign_out(client: SyncGoTrueClient) -> bool:
    try:
        client.sign_out()
    except AuthError as exc:
        _show_auth_error(exc)
        return False
    except httpx.RequestError as exc:
        st.error(f"Could not sign out from Supabase: {exc}")
        return False

    st.session_state.pop("_mars_supabase_client", None)
    st.session_state.pop("_mars_oauth_redirect", None)
    return True
