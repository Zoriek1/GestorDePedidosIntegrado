# -*- coding: utf-8 -*-
"""
Serviço para integração com Meta Conversions API (CAPI)
Envia eventos Purchase para Meta com normalização, hashing e retry
"""
import hashlib
import os
import re
import time
import unicodedata
from typing import Dict, List, Optional, Tuple

import requests

from app.models.pedido import Pedido


class MetaConversionsApiService:
    """
    Serviço para envio de eventos para Meta Conversions API
    """

    def __init__(self):
        """Inicializa o serviço com configurações do .env"""
        self.pixel_id = os.environ.get("META_PIXEL_ID", "")
        self.access_token = os.environ.get("META_CAPI_ACCESS_TOKEN", "")
        self.api_version = os.environ.get("META_CAPI_API_VERSION", "v21.0")
        self.test_event_code = os.environ.get("META_TEST_EVENT_CODE", "")
        self.debug_enabled = os.environ.get("META_CAPI_DEBUG", "false").lower() == "true"

        # Conversions API Gateway (opcional - melhora visualização e métricas)
        self.use_gateway = os.environ.get("META_CAPI_USE_GATEWAY", "false").lower() == "true"
        self.gateway_domain = (
            os.environ.get("META_CAPI_GATEWAY_DOMAIN") or "gestaopedidos.planteumaflor.online"
        )
        self.gateway_endpoint = os.environ.get("META_CAPI_GATEWAY_ENDPOINT") or ""

        # URL base da API
        # Se usar Gateway, o endpoint é no próprio domínio
        # Se não usar, vai direto para a Meta
        if self.use_gateway:
            if self.gateway_endpoint:
                # Se endpoint completo fornecido, usar este
                self.base_url = self.gateway_endpoint
            else:
                # Construir endpoint padrão: https://seu-dominio.com/meta-gateway/{pixel_id}/events
                self.base_url = f"https://{self.gateway_domain}/meta-gateway/{self.pixel_id}/events"
        else:
            # Integração direta com Meta
            self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.pixel_id}/events"

        # Validação básica da URL base
        if self.use_gateway and self.gateway_endpoint:
            if self.gateway_domain and self.gateway_domain not in self.gateway_endpoint:
                self._debug_log(
                    "[META_CAPI] AVISO: META_CAPI_GATEWAY_ENDPOINT nao contem o dominio esperado.",
                    {
                        "gateway_domain": self.gateway_domain,
                        "gateway_endpoint": self.gateway_endpoint,
                    },
                )

        self._debug_log(
            "[META_CAPI] Configuracao inicializada.",
            {
                "use_gateway": self.use_gateway,
                "gateway_domain": self.gateway_domain,
                "gateway_endpoint": bool(self.gateway_endpoint),
                "base_url": self.base_url,
            },
        )

    def _debug_log(self, message: str, data: Optional[Dict] = None) -> None:
        if not self.debug_enabled:
            return
        if data:
            print(f"{message} {data}")
        else:
            print(message)

    def normalize_phone_br_e164(self, telefone: str) -> str:
        """
        Normalização robusta de telefone para formato E.164 BR

        Args:
            telefone: Telefone em qualquer formato

        Returns:
            str: Telefone no formato E.164 (+55DDDNUMERO)

        Raises:
            ValueError: Se telefone inválido (tamanho mínimo não atingido)
        """
        if not telefone:
            raise ValueError("Telefone vazio")

        # Remove tudo que não for dígito
        digits = re.sub(r"[^\d]", "", telefone)

        # Remove "00" inicial se existir
        if digits.startswith("00"):
            digits = digits[2:]

        # Se não começa com 55, prefixar
        if not digits.startswith("55"):
            digits = "55" + digits

        # Validar tamanho mínimo (55 + DDD + número = mínimo 12 dígitos)
        if len(digits) < 12:
            raise ValueError(f"Telefone inválido (muito curto): {telefone}")

        return "+" + digits

    def normalize_fn(self, nome: str) -> str:
        """
        Normalização de primeiro nome para hash

        Args:
            nome: Nome completo ou primeiro nome

        Returns:
            str: Primeiro nome normalizado (lowercase, sem acentos, sem pontuação)
        """
        if not nome:
            return ""

        # Strip e lowercase
        nome = nome.strip().lower()

        # Remove acentos
        nome = unicodedata.normalize("NFKD", nome)
        nome = "".join(c for c in nome if not unicodedata.combining(c))

        # Remove pontuação
        nome = re.sub(r"[^\w\s]", "", nome)

        # Pega primeiro token (antes do primeiro espaço)
        primeiro = nome.split()[0] if nome.split() else nome

        return primeiro

    def hash_sha256(self, value: str) -> str:
        """
        Aplica hash SHA-256 em uma string

        Args:
            value: String para hashear

        Returns:
            str: Hash SHA-256 em hexadecimal
        """
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def normalize_generic(self, value: str) -> str:
        """
        Normaliza string genérica para hashing (lowercase, sem acentos, sem pontuação)
        """
        if not value:
            return ""

        normalized = value.strip().lower()
        normalized = unicodedata.normalize("NFKD", normalized)
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
        normalized = re.sub(r"[^\w]", "", normalized)
        return normalized

    def normalize_email(self, email: str) -> str:
        """Normaliza email para hashing conforme boas prÃ¡ticas da Meta."""
        if not email:
            return ""
        return email.strip().lower()

    def maybe_hash(self, value: str, normalize_fn=None) -> str:
        """
        Aplica hash se valor não estiver em formato SHA-256 hex.
        """
        if not value:
            return ""
        candidate = value.strip()
        if re.fullmatch(r"[a-fA-F0-9]{64}", candidate):
            return candidate.lower()
        normalized = normalize_fn(candidate) if normalize_fn else candidate
        if not normalized:
            return ""
        return self.hash_sha256(normalized)

    def is_valid_fbc(self, value: str) -> bool:
        if not value:
            return False
        return bool(re.fullmatch(r"fb\.1\.\d+\.[A-Za-z0-9_-]+", value.strip()))

    def is_valid_fbp(self, value: str) -> bool:
        if not value:
            return False
        return bool(re.fullmatch(r"fb\.1\.\d+\.\d+", value.strip()))

    def build_fbc_from_fbclid(
        self, fbclid: str, timestamp_source: Optional[object] = None
    ) -> Optional[str]:
        """ConstrÃ³i um valor fbc a partir do fbclid quando necessÃ¡rio."""
        if not fbclid:
            return None

        fbclid_clean = str(fbclid).strip()
        if not fbclid_clean:
            return None

        ts = int(time.time())
        if timestamp_source is not None:
            try:
                if hasattr(timestamp_source, "timestamp"):
                    ts = int(timestamp_source.timestamp())
                else:
                    ts = int(timestamp_source)
            except Exception:
                ts = int(time.time())

        return f"fb.1.{ts}.{fbclid_clean}"

    def parse_brl_money(self, valor_str: str) -> float:
        """
        Converte valor String BRL para float

        Args:
            valor_str: String com valor monetário

        Returns:
            float: Valor convertido, ou 0.0 se inválido
        """
        from app.utils.money import parse_brl_money

        return parse_brl_money(valor_str)

    def determine_action_source(self, pedido: Pedido) -> str:
        """
        Determina action_source dinamicamente baseado na fonte do pedido

        Args:
            pedido: Objeto Pedido

        Returns:
            str: action_source conforme especificação Meta
        """
        # Mapear por fonte_pedido
        if pedido.fonte_pedido_rel:
            fonte_nome = pedido.fonte_pedido_rel.nome.lower()
        elif pedido.fonte_pedido:
            fonte_nome = pedido.fonte_pedido.lower()
        else:
            fonte_nome = ""

        # Mapeamento de fontes conhecidas
        if "whatsapp" in fonte_nome or "dm" in fonte_nome or "chat" in fonte_nome:
            return "chat"
        elif "balcão" in fonte_nome or "loja" in fonte_nome or "física" in fonte_nome:
            return "physical_store"
        elif "telefone" in fonte_nome or "call" in fonte_nome:
            return "phone_call"
        elif "site" in fonte_nome or "web" in fonte_nome:
            return "website"
        else:
            # Default: other (quando não dá para distinguir)
            return "other"

    def resolve_lead_for_purchase(self, pedido: Pedido):
        """Reaproveita o mesmo match de lead usado no fluxo da UTMify."""
        try:
            from app.utils.utmify_helper import resolve_lead_for_pedido

            lead, _match = resolve_lead_for_pedido(pedido)
            return lead
        except Exception:
            return None

    def build_external_id(self, pedido: Pedido, lead=None) -> str:
        """Gera external_id estável com o melhor identificador disponível."""
        if getattr(pedido, "cliente_id", None):
            return f"cliente:{pedido.cliente_id}"

        cliente_rel = getattr(pedido, "cliente_rel", None)
        email = self.normalize_email(getattr(cliente_rel, "email", "") or "")
        if email:
            return f"email:{email}"

        phone_digits = re.sub(r"[^\d]", "", pedido.telefone_cliente or "")
        if phone_digits:
            return f"phone:{phone_digits}"

        if lead and getattr(lead, "fbclid", None):
            return f"fbclid:{str(lead.fbclid).strip()}"

        return f"order:{pedido.id}"

    def build_purchase_event(self, pedido: Pedido) -> Dict:
        """
        Monta payload do evento Purchase para Meta

        Args:
            pedido: Objeto Pedido

        Returns:
            dict: Payload do evento conforme especificação Meta
        """
        # Normalizar e hashear telefone
        try:
            phone_normalized = self.normalize_phone_br_e164(pedido.telefone_cliente)
            phone_hash = self.hash_sha256(phone_normalized)
        except ValueError:
            # Se telefone inválido, usar string vazia (não enviar)
            phone_hash = ""

        # Normalizar e hashear primeiro nome
        primeiro_nome_normalized = self.normalize_fn(pedido.cliente or "")
        fn_hash = self.hash_sha256(primeiro_nome_normalized) if primeiro_nome_normalized else ""

        # Determinar action_source
        action_source = self.determine_action_source(pedido)
        lead = self.resolve_lead_for_purchase(pedido)
        cliente_rel = getattr(pedido, "cliente_rel", None)

        # Obter valor total
        valor_total = pedido.total_pago()

        # Timestamp do evento (usar updated_at quando status mudou, ou created_at)
        event_time = int(
            (pedido.updated_at if pedido.updated_at else pedido.created_at).timestamp()
        )

        # Montar custom_data (apenas campos suportados)
        custom_data = {
            "value": valor_total,
            "currency": "BRL",
            "order_id": str(pedido.id),
        }

        # Validar event_time (Meta não aceita timestamps no futuro)
        now_timestamp = int(time.time())
        max_past = now_timestamp - (7 * 24 * 60 * 60)  # 7 dias no passado

        if event_time > now_timestamp or event_time < max_past:
            # Se evento está no futuro, usar timestamp atual
            event_time = now_timestamp
            # Se evento está muito no passado, usar timestamp atual
            event_time = now_timestamp

        # Validar valor (deve ser positivo)
        if valor_total <= 0:
            valor_total = 0.01  # Valor mínimo para não falhar

        # Dados de localização para user_data (apenas hashes)
        user_location = {}
        if pedido.cidade:
            city_hash = self.maybe_hash(pedido.cidade, normalize_fn=self.normalize_generic)
            if city_hash:
                user_location["ct"] = city_hash

        state_hash = self.maybe_hash("GO", normalize_fn=self.normalize_generic)
        if state_hash:
            user_location["st"] = state_hash

        if pedido.cep:
            cep_normalized = re.sub(r"[^\d]", "", pedido.cep)
            if cep_normalized and len(cep_normalized) == 8:
                zip_hash = self.maybe_hash(cep_normalized)
                if zip_hash:
                    user_location["zp"] = zip_hash

        # Montar payload
        event = {
            "event_name": "Purchase",
            "event_time": event_time,
            "event_id": f"order_{pedido.id}",
            "action_source": action_source,
            "user_data": {},
            "custom_data": custom_data,
        }

        # Adicionar user_data apenas se tiver dados válidos
        # IMPORTANTE: Meta pode exigir pelo menos um campo em user_data
        if phone_hash:
            event["user_data"]["ph"] = [phone_hash]
        if fn_hash:
            event["user_data"]["fn"] = [fn_hash]

        email_normalized = self.normalize_email(getattr(cliente_rel, "email", "") or "")
        if email_normalized:
            event["user_data"]["em"] = [self.hash_sha256(email_normalized)]

        # País fixo (Brasil) - enviar hash conforme especificação CAPI
        country_hash = self.maybe_hash("br", normalize_fn=self.normalize_generic)
        if country_hash:
            event["user_data"]["country"] = country_hash

        # Adicionar fbc e fbp se disponíveis (melhora qualidade de correspondência de eventos)
        # fbc: Facebook Click ID (vem do parâmetro fbclid na URL quando usuário clica em anúncio)
        # fbp: Facebook Browser ID (vem do cookie _fbp criado pelo Pixel do Facebook)
        # IMPORTANTE: Esses valores são case-sensitive e não devem ser normalizados
        lead_fbc = self.build_fbc_from_fbclid(
            getattr(lead, "fbclid", None), getattr(lead, "created_at", None)
        )
        for fbc_candidate in [getattr(pedido, "fbc", None), lead_fbc]:
            if fbc_candidate and self.is_valid_fbc(fbc_candidate):
                event["user_data"]["fbc"] = fbc_candidate
                break
        for fbp_candidate in [getattr(pedido, "fbp", None), getattr(lead, "fbp", None)]:
            if fbp_candidate and self.is_valid_fbp(fbp_candidate):
                event["user_data"]["fbp"] = fbp_candidate
                break
        if lead and getattr(lead, "ip_address", None):
            event["user_data"]["client_ip_address"] = lead.ip_address
        if lead and getattr(lead, "url", None):
            event["event_source_url"] = lead.url

        # Se user_data estiver vazio (sem ph e fn), usar hash do order_id como fallback
        # Isso garante que sempre teremos pelo menos um campo além de country
        external_id_hash = self.hash_sha256(self.build_external_id(pedido, lead))
        event["user_data"]["external_id"] = [external_id_hash]

        # Adicionar dados de localização (se disponíveis) após garantir user_data
        if user_location:
            event["user_data"].update(user_location)

        return event

    def _lead_external_id_hash(self, lead) -> str:
        return self.hash_sha256(f"lead:{lead.id}")

    def _lead_user_data_base(self, lead) -> Dict:
        """fbc/fbp, IP, UA, país, external_id estável (sem PII em claro)."""
        ud: Dict = {}
        lead_fbc = self.build_fbc_from_fbclid(
            getattr(lead, "fbclid", None), getattr(lead, "created_at", None)
        )
        if lead_fbc and self.is_valid_fbc(lead_fbc):
            ud["fbc"] = lead_fbc
        fbp = getattr(lead, "fbp", None)
        if fbp and self.is_valid_fbp(fbp):
            ud["fbp"] = fbp
        if getattr(lead, "ip_address", None):
            ud["client_ip_address"] = lead.ip_address
        ua = getattr(lead, "client_user_agent", None)
        if ua and str(ua).strip():
            ud["client_user_agent"] = str(ua).strip()[:512]
        country_hash = self.maybe_hash("br", normalize_fn=self.normalize_generic)
        if country_hash:
            ud["country"] = country_hash
        ud["external_id"] = [self._lead_external_id_hash(lead)]
        return ud

    def build_contact_event_from_lead(self, lead) -> Dict:
        """
        Evento Contact (clique WhatsApp na landing). value=1, currency BRL.
        event_id deve ser o mesmo enviado pelo Pixel (meta_event_id_contact).
        """
        from app.models.lead import Lead

        if not isinstance(lead, Lead):
            raise TypeError("lead deve ser instância de Lead")
        eid = (getattr(lead, "meta_event_id_contact", None) or "").strip()
        if not eid:
            raise ValueError("meta_event_id_contact ausente no lead")
        ts = lead.created_at.timestamp() if lead.created_at else time.time()
        event_time = int(ts)
        now_timestamp = int(time.time())
        max_past = now_timestamp - (7 * 24 * 60 * 60)
        if event_time > now_timestamp or event_time < max_past:
            event_time = now_timestamp

        user_data = self._lead_user_data_base(lead)
        phone_raw = getattr(lead, "phone", None) or ""
        if phone_raw:
            try:
                phone_norm = self.normalize_phone_br_e164(phone_raw)
                user_data["ph"] = [self.hash_sha256(phone_norm)]
            except ValueError:
                pass

        event = {
            "event_name": "Contact",
            "event_time": event_time,
            "event_id": eid,
            "action_source": "website",
            "event_source_url": (lead.url or "")[:4096] if getattr(lead, "url", None) else None,
            "user_data": user_data,
            "custom_data": {
                "value": 1.0,
                "currency": "BRL",
                "lead_id": str(lead.id),
            },
        }
        return event

    def build_lead_event_from_lead(self, lead, *, event_time_override: Optional[int] = None) -> Dict:
        """
        Evento Lead (telefone salvo). value=15, currency BRL.
        event_id em meta_event_id_lead (novo em relação ao Contact).
        """
        from app.models.lead import Lead

        if not isinstance(lead, Lead):
            raise TypeError("lead deve ser instância de Lead")
        eid = (getattr(lead, "meta_event_id_lead", None) or "").strip()
        if not eid:
            raise ValueError("meta_event_id_lead ausente no lead")
        phone_raw = getattr(lead, "phone", None) or ""
        if not phone_raw:
            raise ValueError("lead sem telefone para evento Lead")

        if event_time_override is not None:
            event_time = int(event_time_override)
        elif lead.updated_at:
            event_time = int(lead.updated_at.timestamp())
        elif lead.created_at:
            event_time = int(lead.created_at.timestamp())
        else:
            event_time = int(time.time())
        now_timestamp = int(time.time())
        max_past = now_timestamp - (7 * 24 * 60 * 60)
        if event_time > now_timestamp or event_time < max_past:
            event_time = now_timestamp

        phone_norm = self.normalize_phone_br_e164(phone_raw)
        phone_hash = self.hash_sha256(phone_norm)

        user_data = self._lead_user_data_base(lead)
        user_data["ph"] = [phone_hash]

        event = {
            "event_name": "Lead",
            "event_time": event_time,
            "event_id": eid,
            "action_source": "website",
            "event_source_url": (lead.url or "")[:4096] if getattr(lead, "url", None) else None,
            "user_data": user_data,
            "custom_data": {
                "value": 15.0,
                "currency": "BRL",
                "lead_id": str(lead.id),
            },
        }
        return event

    def sanitize_event_payload(self, event: Dict) -> Dict:
        """
        Normaliza payload vindo da outbox para evitar parâmetros inválidos.
        """
        sanitized = {
            "event_name": event.get("event_name"),
            "event_time": event.get("event_time"),
            "event_id": event.get("event_id"),
            "action_source": event.get("action_source"),
            "event_source_url": event.get("event_source_url"),
            "user_data": dict(event.get("user_data") or {}),
            "custom_data": dict(event.get("custom_data") or {}),
        }

        # Normalizar e validar event_time (segundos Unix, dentro de 7 dias)
        now_timestamp = int(time.time())
        max_past = now_timestamp - (7 * 24 * 60 * 60)
        event_time = sanitized.get("event_time")
        try:
            if isinstance(event_time, str) and event_time.isdigit():
                event_time = int(event_time)
            elif isinstance(event_time, (int, float)):
                event_time = int(event_time)
            else:
                event_time = now_timestamp

            # Se estiver em milissegundos, normalizar para segundos
            if event_time > 10_000_000_000:
                event_time = int(event_time / 1000)

            if event_time > now_timestamp or event_time < max_past:
                event_time = now_timestamp
        except Exception:
            event_time = now_timestamp

        sanitized["event_time"] = event_time

        # Remover chaves de localização inválidas do custom_data
        city = sanitized["custom_data"].pop("city", None)
        state = sanitized["custom_data"].pop("state", None)
        zip_code = sanitized["custom_data"].pop("zip_code", None)
        sanitized["custom_data"].pop("latitude", None)
        sanitized["custom_data"].pop("longitude", None)

        # Normalizar country se veio em texto
        if "country" in sanitized["user_data"]:
            country_value = sanitized["user_data"]["country"]
            country_hash = self.maybe_hash(str(country_value), normalize_fn=self.normalize_generic)
            if country_hash:
                sanitized["user_data"]["country"] = country_hash

        # Mapear localização para user_data (hash)
        if city:
            city_hash = self.maybe_hash(str(city), normalize_fn=self.normalize_generic)
            if city_hash:
                sanitized["user_data"]["ct"] = city_hash
        if state:
            state_hash = self.maybe_hash(str(state), normalize_fn=self.normalize_generic)
            if state_hash:
                sanitized["user_data"]["st"] = state_hash
        if zip_code:
            zip_digits = re.sub(r"[^\d]", "", str(zip_code))
            if len(zip_digits) == 8:
                zip_hash = self.maybe_hash(zip_digits)
                if zip_hash:
                    sanitized["user_data"]["zp"] = zip_hash

        # Validar fbc/fbp se presentes
        if "fbc" in sanitized["user_data"] and not self.is_valid_fbc(sanitized["user_data"]["fbc"]):
            sanitized["user_data"].pop("fbc", None)
        if "fbp" in sanitized["user_data"] and not self.is_valid_fbp(sanitized["user_data"]["fbp"]):
            sanitized["user_data"].pop("fbp", None)

        return sanitized

    def send_events(self, events: List[Dict]) -> Dict:
        """
        Envia lote interno de eventos para Meta Conversions API

        Nota: Este é um "lote interno" para organização, não Graph Batch API.
        Pode enviar até ~1000 eventos por request (usar 50 por segurança).

        Args:
            events: Lista de eventos (dicts) para enviar

        Returns:
            dict: Resposta da API Meta com events_received, fbtrace_id, etc.
        """
        if not self.pixel_id or not self.access_token:
            error_msg = "META_PIXEL_ID e META_CAPI_ACCESS_TOKEN devem estar configurados no .env"
            return {
                "_status_code": 0,
                "_error": error_msg,
                "error": {"message": error_msg},
                "events_received": 0,
            }

        if not events:
            return {"events_received": 0, "message": "Nenhum evento para enviar"}

        # Montar payload
        payload = {"data": events}

        # Adicionar test_event_code se configurado
        # Nota: Se já estiver no payload (vindo do Gateway), não adicionar novamente
        if self.test_event_code and "test_event_code" not in payload:
            payload["test_event_code"] = self.test_event_code

        # Headers
        headers = {"Content-Type": "application/json"}

        # Query params e headers dependem do método usado
        if self.use_gateway:
            # Gateway: access_token vai no header Authorization
            headers["Authorization"] = f"Bearer {self.access_token}"
            params = {}
        else:
            # Integração direta: access_token vai no query param
            params = {"access_token": self.access_token}

        self._debug_log(
            "[META_CAPI] Enviando eventos.",
            {
                "base_url": self.base_url,
                "use_gateway": self.use_gateway,
                "headers": {
                    "Content-Type": headers.get("Content-Type"),
                    "Authorization": "Bearer ***" if headers.get("Authorization") else None,
                },
                "params": {"access_token": "***"} if params else {},
                "events_count": len(events),
            },
        )

        try:
            # Enviar requisição
            response = requests.post(
                self.base_url, json=payload, headers=headers, params=params, timeout=30
            )

            # Parse resposta
            response.raise_for_status()
            result = response.json()

            # Adicionar status_code para classificação de erros
            result["_status_code"] = response.status_code

            self._debug_log(
                "[META_CAPI] Resposta recebida.",
                {"status_code": response.status_code, "body_keys": list(result.keys())},
            )

            return result

        except requests.exceptions.RequestException as e:
            # Capturar erro de requisição
            status_code = getattr(e.response, "status_code", 0) if hasattr(e, "response") else 0
            error_msg = str(e)

            # Tentar parsear resposta de erro se disponível
            error_response = {}
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_response = e.response.json()
                    # Capturar mensagem detalhada da Meta (direta ou via Gateway)
                    meta_error = None
                    if "details" in error_response and isinstance(error_response["details"], dict):
                        meta_error = error_response["details"].get("error")
                    if not meta_error and "error" in error_response:
                        meta_error = error_response["error"]

                    if isinstance(meta_error, dict):
                        error_msg = meta_error.get("message", error_msg)
                        # Adicionar código de erro se disponível
                        if "code" in meta_error:
                            error_msg = f"[{meta_error['code']}] {error_msg}"
                        if "error_subcode" in meta_error:
                            error_msg += f" (subcode: {meta_error['error_subcode']})"
                        # Adicionar tipo de erro se disponível
                        if "type" in meta_error:
                            error_msg += f" (type: {meta_error['type']})"
                    elif isinstance(meta_error, str):
                        error_msg = meta_error
                except Exception:
                    error_response = {"error": {"message": error_msg}}

            error_response["_status_code"] = status_code
            error_response["_error"] = error_msg

            self._debug_log(
                "[META_CAPI] Erro na requisicao.",
                {"status_code": status_code, "error": error_msg},
            )

            return error_response

    def send_single_event(self, pedido: Pedido) -> Dict:
        """
        Wrapper para enviar um único evento

        Args:
            pedido: Objeto Pedido

        Returns:
            dict: Resposta da API Meta
        """
        event = self.build_purchase_event(pedido)
        return self.send_events([event])

    def classify_error(self, response: Dict, status_code: int) -> Tuple[str, bool]:
        """
        Classifica erro como retryable ou permanent

        Args:
            response: Resposta da API (pode conter erro)
            status_code: Código HTTP da resposta

        Returns:
            tuple: (error_type, is_retryable)
                - error_type: "retryable" ou "permanent"
                - is_retryable: True se deve tentar novamente
        """
        # Erro de configuração (credenciais não configuradas) = permanente
        error_msg = str(response.get("_error", "")).lower()
        if "deve estar configurado" in error_msg or "não configurado" in error_msg:
            return ("permanent", False)

        # Retryable: timeout, 5xx, 429 (rate limit)
        if status_code == 429:  # Rate limit
            return ("retryable", True)
        if 500 <= status_code < 600:  # Server errors
            return ("retryable", True)
        if status_code == 0:  # Timeout ou erro de conexão (mas não configuração)
            # Verificar se é erro de configuração
            if "configurado" not in error_msg:
                return ("retryable", True)
            else:
                return ("permanent", False)

        # Permanent: token inválido, payload inválido, permissão
        if status_code == 401:  # Unauthorized (token inválido)
            return ("permanent", False)
        if status_code == 403:  # Forbidden (sem permissão)
            return ("permanent", False)
        if status_code == 400:  # Bad Request (payload inválido)
            # Verificar se é erro de validação
            error_field = response.get("error")
            if isinstance(error_field, dict):
                error_msg = str(error_field.get("message", "")).lower()
            elif isinstance(error_field, str):
                error_msg = error_field.lower()
            else:
                error_msg = ""
            if "validation" in error_msg or "invalid" in error_msg:
                return ("permanent", False)
            # Pode ser retryable em alguns casos
            return ("retryable", True)

        # Default: considerar como retryable (erro desconhecido)
        return ("retryable", True)
