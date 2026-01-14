# -*- coding: utf-8 -*-
"""
Serviço para integração com Meta Conversions API (CAPI)
Envia eventos Purchase para Meta com normalização, hashing e retry
"""
import hashlib
import os
import re
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
        
        # Conversions API Gateway (opcional - melhora visualização e métricas)
        self.use_gateway = os.environ.get("META_CAPI_USE_GATEWAY", "false").lower() == "true"
        self.gateway_domain = os.environ.get("META_CAPI_GATEWAY_DOMAIN") or "gestaopedidos.planteumaflor.online"
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

        # Obter valor total
        valor_total = pedido.total_pago()

        # Timestamp do evento (usar updated_at quando status mudou, ou created_at)
        event_time = int(
            (pedido.updated_at if pedido.updated_at else pedido.created_at).timestamp()
        )

        # Montar custom_data com localização
        custom_data = {
            "value": valor_total,
            "currency": "BRL",
            "order_id": str(pedido.id),
        }

        # Adicionar campos de localização se disponíveis
        # Cidade
        if pedido.cidade:
            custom_data["city"] = pedido.cidade.strip()

        # Estado (padrão GO para Goiás, ou extrair do endereço se disponível)
        # Como todos os pedidos são de Goiânia/GO, usar "GO" como padrão
        custom_data["state"] = "GO"

        # CEP (normalizar: remover hífen e espaços)
        if pedido.cep:
            cep_normalized = re.sub(r"[^\d]", "", pedido.cep)
            if cep_normalized:
                custom_data["zip_code"] = cep_normalized

        # Coordenadas (latitude e longitude) - se disponíveis
        if pedido.coords_lat and pedido.coords_lon:
            custom_data["latitude"] = float(pedido.coords_lat)
            custom_data["longitude"] = float(pedido.coords_lon)

        # Validar event_time (Meta aceita até ~7 dias no futuro e ~7 dias no passado)
        import time
        now_timestamp = int(time.time())
        max_future = now_timestamp + (7 * 24 * 60 * 60)  # 7 dias no futuro
        max_past = now_timestamp - (7 * 24 * 60 * 60)  # 7 dias no passado
        
        if event_time > max_future:
            # Se evento está muito no futuro, usar timestamp atual
            event_time = now_timestamp
        elif event_time < max_past:
            # Se evento está muito no passado, usar timestamp atual
            event_time = now_timestamp

        # Validar valor (deve ser positivo)
        if valor_total <= 0:
            valor_total = 0.01  # Valor mínimo para não falhar

        # Validar coordenadas se presentes
        if "latitude" in custom_data:
            lat = custom_data["latitude"]
            lon = custom_data["longitude"]
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                # Remover coordenadas inválidas
                custom_data.pop("latitude", None)
                custom_data.pop("longitude", None)

        # Validar CEP (deve ter 8 dígitos)
        if "zip_code" in custom_data:
            zip_code = custom_data["zip_code"]
            if len(zip_code) != 8 or not zip_code.isdigit():
                custom_data.pop("zip_code", None)

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
        
        # País fixo (Brasil) - todos os pedidos são de Goiânia/GO
        event["user_data"]["country"] = "BR"
        
        # Adicionar fbc e fbp se disponíveis (melhora qualidade de correspondência de eventos)
        # fbc: Facebook Click ID (vem do parâmetro fbclid na URL quando usuário clica em anúncio)
        # fbp: Facebook Browser ID (vem do cookie _fbp criado pelo Pixel do Facebook)
        # IMPORTANTE: Esses valores são case-sensitive e não devem ser normalizados
        if hasattr(pedido, "fbc") and pedido.fbc:
            event["user_data"]["fbc"] = pedido.fbc
        if hasattr(pedido, "fbp") and pedido.fbp:
            event["user_data"]["fbp"] = pedido.fbp
        
        # Se user_data estiver vazio (sem ph e fn), usar hash do order_id como fallback
        # Isso garante que sempre teremos pelo menos um campo além de country
        if not phone_hash and not fn_hash:
            # Usar external_id como fallback (hash do order_id)
            external_id_hash = self.hash_sha256(str(pedido.id))
            event["user_data"]["external_id"] = [external_id_hash]

        return event

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
                    # Capturar mensagem detalhada da Meta
                    if "error" in error_response:
                        meta_error = error_response["error"]
                        error_msg = meta_error.get("message", error_msg)
                        # Adicionar código de erro se disponível
                        if "code" in meta_error:
                            error_msg = f"[{meta_error['code']}] {error_msg}"
                        if "error_subcode" in meta_error:
                            error_msg += f" (subcode: {meta_error['error_subcode']})"
                        # Adicionar tipo de erro se disponível
                        if "type" in meta_error:
                            error_msg += f" (type: {meta_error['type']})"
                except Exception:
                    error_response = {"error": {"message": error_msg}}

            error_response["_status_code"] = status_code
            error_response["_error"] = error_msg

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
            error_msg = str(response.get("error", {}).get("message", "")).lower()
            if "validation" in error_msg or "invalid" in error_msg:
                return ("permanent", False)
            # Pode ser retryable em alguns casos
            return ("retryable", True)

        # Default: considerar como retryable (erro desconhecido)
        return ("retryable", True)
