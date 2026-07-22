from contextlib import contextmanager
from typing import Any, Iterator

from app.services.integration_settings_service import runtime_config

SECRET_KEYS = {"META_CAPI_ACCESS_TOKEN", "GA4_API_SECRET", "UTMIFY_API_TOKEN"}


@contextmanager
def secure_runtime_config(store_ref_id: int) -> Iterator[dict[str, Any]]:
    config = runtime_config(store_ref_id)
    try:
        yield config
    finally:
        for key in SECRET_KEYS:
            if key in config:
                config[key] = None
        del config
        import gc

        gc.collect()
