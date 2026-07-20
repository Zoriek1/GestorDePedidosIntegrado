# -*- coding: utf-8 -*-
"""OAuth/token service da integracao Bling."""

import base64
import json
from datetime import timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from flask import current_app

from app import db
from app.integrations.bling.errors import BlingConfigError, BlingRetryableError
from app.models.bling_credential import BlingCredential
from app.models.pedido import datetime_now_brazil
from app.utils.crypto import decrypt_secret, derive_key, encrypt_secret

BLING_CRYPTO_PURPOSE = b":bling-oauth"


class BlingTokenService:
    @staticmethod
    def _store_id() -> str:
        return current_app.config.get("BLING_STORE_ID") or "default"

    @staticmethod
    def _auth_base_url() -> str:
        return (current_app.config.get("BLING_AUTH_BASE_URL") or "").rstrip("/")

    @staticmethod
    def _token_url() -> str:
        return f"{BlingTokenService._auth_base_url()}/token"

    @staticmethod
    def _authorize_url() -> str:
        return f"{BlingTokenService._auth_base_url()}/authorize"

    @staticmethod
    def _require_config() -> None:
        required = ["BLING_CLIENT_ID", "BLING_CLIENT_SECRET", "BLING_REDIRECT_URI"]
        missing = [key for key in required if not current_app.config.get(key)]
        if missing:
            raise BlingConfigError(
                "Credenciais Bling nao configuradas",
                details={"required_env": missing},
            )

    @staticmethod
    def _key() -> bytes:
        try:
            return derive_key(BLING_CRYPTO_PURPOSE)
        except RuntimeError as exc:
            raise BlingConfigError("SECRET_KEY obrigatoria para criptografar tokens Bling") from exc

    @staticmethod
    def encrypt(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return encrypt_secret(value, BLING_CRYPTO_PURPOSE)
        except RuntimeError as exc:
            raise BlingConfigError("SECRET_KEY obrigatoria para criptografar tokens Bling") from exc

    @staticmethod
    def decrypt(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return decrypt_secret(value, BLING_CRYPTO_PURPOSE)
        except RuntimeError as exc:
            raise BlingConfigError(
                "SECRET_KEY obrigatoria para descriptografar tokens Bling"
            ) from exc

    @staticmethod
    def _basic_auth_header() -> str:
        client_id = current_app.config.get("BLING_CLIENT_ID") or ""
        client_secret = current_app.config.get("BLING_CLIENT_SECRET") or ""
        raw = f"{client_id}:{client_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    @staticmethod
    def build_authorize_url(state: Optional[str] = None) -> str:
        BlingTokenService._require_config()
        params = {
            "response_type": "code",
            "client_id": current_app.config["BLING_CLIENT_ID"],
            "redirect_uri": current_app.config["BLING_REDIRECT_URI"],
        }
        if state:
            params["state"] = state
        return f"{BlingTokenService._authorize_url()}?{urlencode(params)}"

    @staticmethod
    def _post_token(data: Dict[str, Any]) -> Dict[str, Any]:
        BlingTokenService._require_config()
        response = requests.post(
            BlingTokenService._token_url(),
            data=data,
            headers={
                "Authorization": BlingTokenService._basic_auth_header(),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "enable-jwt": "1",
            },
            timeout=int(current_app.config.get("BLING_TIMEOUT_SECONDS") or 20),
        )
        try:
            payload = response.json()
        except Exception:
            payload = {"raw_text": response.text[:1000]}
        payload["_status_code"] = response.status_code
        if response.status_code >= 400:
            raise BlingRetryableError(
                "Falha ao obter token Bling",
                details={"status_code": response.status_code, "response": payload},
            )
        return payload

    @staticmethod
    def exchange_code(code: str) -> BlingCredential:
        payload = BlingTokenService._post_token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": current_app.config.get("BLING_REDIRECT_URI"),
            }
        )
        return BlingTokenService.save_token_payload(payload)

    @staticmethod
    def refresh_access_token(credential: Optional[BlingCredential] = None) -> BlingCredential:
        credential = credential or BlingTokenService.get_credential()
        refresh_token = BlingTokenService.decrypt(credential.refresh_token_encrypted)
        if not refresh_token:
            raise BlingConfigError("Refresh token Bling ausente")
        payload = BlingTokenService._post_token(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )
        return BlingTokenService.save_token_payload(payload, credential=credential)

    @staticmethod
    def save_token_payload(
        payload: Dict[str, Any],
        *,
        credential: Optional[BlingCredential] = None,
    ) -> BlingCredential:
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        if not access_token:
            raise BlingConfigError(
                "Resposta OAuth do Bling sem access_token",
                details={"status_code": payload.get("_status_code")},
            )

        store_id = BlingTokenService._store_id()
        credential = credential or BlingCredential.query.filter_by(store_id=store_id).first()
        if not credential:
            credential = BlingCredential(store_id=store_id)
            db.session.add(credential)

        expires_in = int(payload.get("expires_in") or 0)
        credential.access_token_encrypted = BlingTokenService.encrypt(access_token)
        if refresh_token:
            credential.refresh_token_encrypted = BlingTokenService.encrypt(refresh_token)
        credential.token_type = payload.get("token_type") or "Bearer"
        credential.scopes = payload.get("scope")
        credential.expires_at = (
            datetime_now_brazil() + timedelta(seconds=max(expires_in - 60, 60))
            if expires_in
            else None
        )
        credential.active = True
        credential.raw_json = json.dumps(
            {k: v for k, v in payload.items() if k not in {"access_token", "refresh_token"}},
            ensure_ascii=True,
        )
        credential.updated_at = datetime_now_brazil()
        db.session.commit()
        return credential

    @staticmethod
    def get_credential() -> BlingCredential:
        credential = BlingCredential.query.filter_by(
            store_id=BlingTokenService._store_id(), active=True
        ).first()
        if not credential:
            raise BlingConfigError("Bling ainda nao conectado")
        return credential

    @staticmethod
    def _is_expired(expires_at) -> bool:
        if not expires_at:
            return False
        now = datetime_now_brazil()
        if expires_at.tzinfo is None or expires_at.tzinfo.utcoffset(expires_at) is None:
            expires_at = expires_at.replace(tzinfo=now.tzinfo)
        return expires_at <= now

    @staticmethod
    def get_valid_access_token() -> str:
        credential = BlingTokenService.get_credential()
        if BlingTokenService._is_expired(credential.expires_at):
            credential = BlingTokenService.refresh_access_token(credential)
        token = BlingTokenService.decrypt(credential.access_token_encrypted)
        if not token:
            raise BlingConfigError("Access token Bling ausente")
        return token
