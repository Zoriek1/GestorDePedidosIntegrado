# -*- coding: utf-8 -*-
"""Resolve `value` por evento (Contact/Lead) a partir de UTM do lead.

Lookup case-insensitive por `utm_content` contra
`backend/config/meta_capi_value_map.json`. Quando UTM não bate ou está
ausente, devolve `default` do mesmo arquivo. Cache em memória — recarrega
apenas se o mtime do arquivo mudar.
"""
import json
import os
import threading
from typing import Dict, Optional

_DEFAULT_FALLBACK = {
    "default": {"contact": 10.0, "lead": 50.0},
    "by_utm_content": {},
}

_lock = threading.Lock()
_cache: Dict[str, object] = {"path": None, "mtime": None, "data": None}


def _config_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "config", "meta_capi_value_map.json")


def _load(path: str) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return dict(_DEFAULT_FALLBACK)
    except Exception:
        return dict(_DEFAULT_FALLBACK)

    if not isinstance(data, dict):
        return dict(_DEFAULT_FALLBACK)
    data.setdefault("default", _DEFAULT_FALLBACK["default"])
    data.setdefault("by_utm_content", {})
    return data


def _get_config() -> Dict:
    path = _config_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None

    with _lock:
        if _cache["data"] is None or _cache["path"] != path or _cache["mtime"] != mtime:
            _cache["path"] = path
            _cache["mtime"] = mtime
            _cache["data"] = _load(path)
        return _cache["data"]  # type: ignore[return-value]


def _utm_key(lead) -> Optional[str]:
    utm = getattr(lead, "utm_content", None) or getattr(lead, "utm_campaign", None)
    if not utm:
        return None
    raw = str(utm).strip().upper()
    # Meta Ads entrega utm_content como "CARRO | LOW-TCK|120247480286290017":
    # espaços ao redor do pipe + ID numérico do adgroup colado no fim.
    # Normalizar pra bater com as chaves do map (ex: "CARRO|LOW-TCK").
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    while parts and parts[-1].isdigit():
        parts.pop()
    if not parts:
        return None
    return "|".join(parts)


def resolve_value(lead, event_type: str) -> float:
    """Devolve value para o evento (`contact` ou `lead`).

    Lookup por `utm_content` (fallback `utm_campaign`) contra
    `by_utm_content`. Se UTM ausente ou desconhecido, usa `default`.
    """
    cfg = _get_config()
    key = _utm_key(lead)
    table = cfg.get("by_utm_content") or {}
    if key and key in table:
        bucket = table[key]
    else:
        bucket = cfg.get("default") or _DEFAULT_FALLBACK["default"]
    try:
        return float(bucket.get(event_type, 0.0))
    except (TypeError, ValueError):
        return 0.0


def reset_cache_for_tests() -> None:
    """Reseta o cache — usar apenas em testes."""
    with _lock:
        _cache["path"] = None
        _cache["mtime"] = None
        _cache["data"] = None
