# -*- coding: utf-8 -*-
"""Utilitários de logging para a aplicação."""
from __future__ import annotations

import logging
from typing import Any


def _resolve_debug(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    value_str = str(value).strip().lower()
    return value_str in {"1", "true", "yes", "on", "debug"}


def configure_logging(debug: Any = False) -> None:
    """Configura o logger raiz respeitando o modo debug da aplicação."""
    level = logging.DEBUG if _resolve_debug(debug) else logging.INFO
    root_logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
