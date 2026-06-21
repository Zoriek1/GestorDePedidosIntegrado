# -*- coding: utf-8 -*-
"""Erros da integracao Bling."""


class BlingIntegrationError(Exception):
    """Erro esperado da integracao Bling."""

    retryable = False
    code = "bling_error"

    def __init__(self, message: str, *, details=None):
        super().__init__(message)
        self.details = details or {}


class BlingConfigError(BlingIntegrationError):
    code = "bling_config_error"


class BlingValidationError(BlingIntegrationError):
    code = "bling_validation_error"


class BlingRetryableError(BlingIntegrationError):
    retryable = True
    code = "bling_retryable_error"


class BlingApiError(BlingRetryableError):
    code = "bling_api_error"

    def __init__(self, message: str, *, status_code=None, payload=None, details=None):
        super().__init__(message, details=details)
        self.status_code = status_code
        self.payload = payload
        if status_code and 400 <= int(status_code) < 500 and int(status_code) not in (408, 409, 429):
            self.retryable = False
