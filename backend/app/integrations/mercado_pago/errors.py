# -*- coding: utf-8 -*-
"""Hierarquia de erros da integracao Mercado Pago Point."""


class MercadoPagoError(Exception):
    """Base para erros da integracao MP."""

    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message)
        self.details = details or {}


class MercadoPagoConfigError(MercadoPagoError):
    """Configuracao ausente ou invalida."""


class MercadoPagoValidationError(MercadoPagoError):
    """Dados invalidos - nao retryable."""


class MercadoPagoRetryableError(MercadoPagoError):
    """Erro temporario - retryable."""


class MercadoPagoApiError(MercadoPagoRetryableError):
    """Erro da API do Mercado Pago."""

    def __init__(
        self,
        message: str = "",
        status_code: int = None,
        payload: dict = None,
        details: dict = None,
    ):
        super().__init__(message, details=details)
        self.status_code = status_code
        self.payload = payload or {}

    @property
    def is_retryable(self) -> bool:
        if self.status_code in (401, 403, 404, 422):
            return False
        return True
