import logging
import os
from typing import Optional
import jwt

logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "webgis-production-secret-key-lan-2026-super-secure")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            logger.warning("Token provided is not an access token (type: %s)", payload.get("type"))
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Access token has expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid access token: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error decoding token: %s", exc)
        return None
