from typing import Optional
import jwt

JWT_SECRET_KEY = "webgis_super_secret_jwt_key_2026_seismic_data_serving"
JWT_ALGORITHM = "HS256"


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None
