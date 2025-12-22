# -*- coding: utf-8 -*-
"""
Cliente HTTP reutilizável com timeout padrão e retry opcional.
"""
from __future__ import annotations

from typing import Iterable, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """Wrapper simples do requests.Session com retry opcional."""

    def __init__(
        self,
        timeout: int = 10,
        retries: int = 0,
        backoff_factor: float = 0.3,
        status_forcelist: Optional[Iterable[int]] = None,
        allowed_methods: Optional[Iterable[str]] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()

        if retries and retries > 0:
            retry = Retry(
                total=retries,
                backoff_factor=backoff_factor,
                status_forcelist=tuple(status_forcelist or (500, 502, 503, 504)),
                allowed_methods=tuple(allowed_methods or ("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS")),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def request(self, method: str, url: str, timeout: Optional[int] = None, **kwargs):
        return self.session.request(method, url, timeout=timeout or self.timeout, **kwargs)

    def get(self, url: str, timeout: Optional[int] = None, **kwargs):
        return self.request("GET", url, timeout=timeout, **kwargs)

    def post(self, url: str, timeout: Optional[int] = None, **kwargs):
        return self.request("POST", url, timeout=timeout, **kwargs)
