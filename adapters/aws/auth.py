"""JWT bearer stub auth for AWS Lambda handlers (DES-0005-E / Q-AWS-1).

Adapter-local only — core stays agnostic of JWT. Missing/invalid → HTTP 401
(distinct from Gatekeeper denial). Aligns with adapters/onprem/auth.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import jwt


@dataclass(frozen=True)
class AuthPrincipal:
    """Adapter-local principal; not stored on the traveler core schema."""

    subject: str
    claims: dict[str, Any]


class AuthError(Exception):
    """Raised when bearer auth fails; handlers map to HTTP 401."""

    def __init__(self, detail: str = "unauthorized") -> None:
        super().__init__(detail)
        self.detail = detail


def jwt_secret() -> str:
    secret = os.environ.get("HEXTORY_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "HEXTORY_JWT_SECRET is required for AWS JWT auth "
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
    """Helper for tests / LocalStack smoke — HS256 bearer token."""
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
        raise AuthError("invalid or expired bearer token") from exc
    subject = str(claims.get("sub") or "")
    if not subject:
        raise AuthError("bearer token missing subject")
    return AuthPrincipal(subject=subject, claims=dict(claims))


def require_bearer(authorization_header: Optional[str]) -> AuthPrincipal:
    """Validate ``Authorization: Bearer <jwt>`` from API Gateway headers."""
    if not authorization_header or not authorization_header.strip():
        raise AuthError("missing bearer token")
    parts = authorization_header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AuthError("missing bearer token")
    return decode_token(parts[1].strip())
