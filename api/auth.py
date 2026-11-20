"""Supabase-backed authentication for protected API routes."""

import os

import httpx
from fastapi import Header, HTTPException, status


async def require_authenticated_user(
    authorization: str | None = Header(default=None),
) -> dict:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on the API server.",
        )

    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Supabase access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": anon_key,
                    "Authorization": f"Bearer {token.strip()}",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not validate the session with Supabase.",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Supabase access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase could not validate the session.",
        )

    try:
        user = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase returned an invalid session response.",
        ) from exc
    if not isinstance(user, dict) or not isinstance(user.get("id"), str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase did not return a valid user session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
