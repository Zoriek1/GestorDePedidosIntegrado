"""
Verificação de HMAC para Webhooks Nuvemshop.
"""

import hashlib
import hmac
from typing import Optional


def verify_nuvemshop_hmac(
    raw_body: bytes,
    provided_hmac: Optional[str],
    secret: str,
) -> bool:
    if not provided_hmac or not secret:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, provided_hmac)
