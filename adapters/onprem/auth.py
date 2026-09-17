"""JWT bearer auth for on-prem workflow routes (DES-0004-B / Q-ONP-1).

Adapter-local only — core stays agnostic of JWT. Missing/invalid → HTTP 401.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthPrincipal:
    """Adapter-local principal; not stored on the traveler core schema."""

    subject: str
    claims: dict[str, Any]


def jwt_secret() -> str:
    secret = os.environ.get("HEXTORY_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "HEXTORY_JWT_SECRET is required for on-prem JWT auth "
            "(set a non-empty secret before serving workflow routes)"
        )
    return secret


def jwt_issuer() -> Optional[str]:
    value = os.environ.get("HEXTORY_JWT_ISSUER", "").strip()
    return value or None


def jwt_audience() -> Optional[str]:
    value = os.environ.get("HEXTORY_JWT_AUDIENCE", "").strip()
    return value or None


def mint_token(
    subject: str = "ops",
    *,
    secret: Optional[str] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Helper for tests / local smoke — HS256 bearer token."""
    payload: dict[str, Any] = {"sub": subject}
    if extra_claims:
        payload.update(extra_claims)
    iss = issuer if issuer is not None else jwt_issuer()
    aud = audience if audience is not None else jwt_audience()
    if iss:
        payload["iss"] = iss
    if aud:
        payload["aud"] = aud
    return jwt.encode(payload, secret or jwt_secret(), algorithm="HS256")


def decode_token(token: str, *, secret: Optional[str] = None) -> AuthPrincipal:
    options: dict[str, Any] = {}
    kwargs: dict[str, Any] = {
        "algorithms": ["HS256"],
        "key": secret or jwt_secret(),
    }
    iss = jwt_issuer()
    aud = jwt_audience()
    if iss:
        kwargs["issuer"] = iss
    else:
        options["verify_iss"] = False
    if aud:
        kwargs["audience"] = aud
    else:
        options["verify_aud"] = False
    if options:
        kwargs["options"] = options
    try:
        claims = jwt.decode(token, **kwargs)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    subject = str(claims.get("sub") or "")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthPrincipal(subject=subject, claims=dict(claims))


def require_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)
