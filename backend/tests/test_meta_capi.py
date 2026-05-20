# -*- coding: utf-8 -*-
"""
Testes Unitários: Meta Conversions API Service e Outbox
Testa normalização de dados, hashing, sanitização de payload e fluxo de outbox
"""
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestMetaCapiServiceNormalization:
    """Testes de normalização de dados para Meta CAPI"""

    @pytest.fixture
    def service(self):
        """Cria instância do serviço com configuração mockada"""
        # Mockar variáveis de ambiente
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
                "META_CAPI_DEBUG": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_normalize_phone_br_e164_simple(self, service):
        """Normaliza telefone simples"""
        result = service.normalize_phone_br_e164("62999887766")
        assert result == "+5562999887766"

    def test_normalize_phone_br_e164_with_country_code(self, service):
        """Mantém código do país se já presente"""
        result = service.normalize_phone_br_e164("5562999887766")
        assert result == "+5562999887766"

    def test_normalize_phone_br_e164_with_formatting(self, service):
        """Remove formatação"""
        result = service.normalize_phone_br_e164("(62) 99988-7766")
        assert result == "+5562999887766"

    def test_normalize_phone_br_e164_with_plus(self, service):
        """Remove + e mantém dígitos"""
        result = service.normalize_phone_br_e164("+55 62 99988-7766")
        assert result == "+5562999887766"

    def test_normalize_phone_br_e164_invalid_short(self, service):
        """Rejeita telefone muito curto"""
        with pytest.raises(ValueError, match="muito curto"):
            service.normalize_phone_br_e164("123")

    def test_normalize_phone_br_e164_empty(self, service):
        """Rejeita telefone vazio"""
        with pytest.raises(ValueError, match="vazio"):
            service.normalize_phone_br_e164("")

    def test_normalize_fn_simple(self, service):
        """Normaliza primeiro nome simples"""
        result = service.normalize_fn("João")
        assert result == "joao"

    def test_normalize_fn_with_surname(self, service):
        """Extrai apenas primeiro nome"""
        result = service.normalize_fn("Maria da Silva")
        assert result == "maria"

    def test_normalize_fn_with_accents(self, service):
        """Remove acentos"""
        result = service.normalize_fn("José")
        assert result == "jose"

    def test_normalize_fn_with_punctuation(self, service):
        """Remove pontuação"""
        result = service.normalize_fn("D'Ávila")
        assert result == "davila"

    def test_normalize_fn_empty(self, service):
        """Retorna vazio para entrada vazia"""
        result = service.normalize_fn("")
        assert result == ""

    def test_hash_sha256_consistent(self, service):
        """Hash é consistente"""
        hash1 = service.hash_sha256("test")
        hash2 = service.hash_sha256("test")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 = 64 caracteres hex

    def test_normalize_generic_city(self, service):
        """Normaliza cidade"""
        result = service.normalize_generic("São Paulo")
        assert result == "saopaulo"

    def test_normalize_generic_state(self, service):
        """Normaliza estado"""
        result = service.normalize_generic("GO")
        assert result == "go"

    def test_maybe_hash_already_hashed(self, service):
        """Não re-hasheia valor já hasheado"""
        # SHA-256 de "test"
        already_hashed = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        result = service.maybe_hash(already_hashed)
        assert result == already_hashed

    def test_maybe_hash_plain_value(self, service):
        """Hasheia valor não hasheado"""
        result = service.maybe_hash("test")
        expected = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        assert result == expected


class TestMetaCapiLeadFunnelPayload:
    """Contact / Lead (funil landing) — valores e currency."""

    @pytest.fixture
    def service(self):
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_build_contact_and_lead_events(self, service):
        from datetime import datetime, timezone

        from app.models.lead import Lead

        lead = Lead(
            dedup_key="ut-meta-funnel",
            meta_event_id_contact="contact_st_1",
            url="https://lp.test/p",
            fbclid="IwARx",
            fbp="fb.1.1700000000.999",
            ip_address="192.0.2.10",
            client_user_agent="pytest-ua",
            phone="62999887766",
        )
        lead.id = 7
        lead.created_at = datetime(2025, 6, 1, 15, 0, 0, tzinfo=timezone.utc)

        ce = service.build_contact_event_from_lead(lead)
        assert ce["event_name"] == "Contact"
        assert ce["event_id"] == "contact_st_1"
        assert ce["action_source"] == "website"
        assert ce["custom_data"]["value"] == 1.0
        assert ce["custom_data"]["currency"] == "BRL"
        assert ce["custom_data"]["lead_id"] == "7"
        assert "ph" in ce["user_data"]

        lead.meta_event_id_lead = "lead_st_2"
        lead.updated_at = datetime(2025, 6, 1, 16, 0, 0, tzinfo=timezone.utc)
        le = service.build_lead_event_from_lead(lead)
        assert le["event_name"] == "Lead"
        assert le["event_id"] == "lead_st_2"
        assert le["custom_data"]["value"] == 15.0
        assert le["custom_data"]["currency"] == "BRL"
        assert "ph" in le["user_data"]


class TestMetaCapiServiceValidation:
    """Testes de validação de fbc e fbp"""

    @pytest.fixture
    def service(self):
        """Cria instância do serviço com configuração mockada"""
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_is_valid_fbc_correct_format(self, service):
        """Valida fbc com formato correto"""
        result = service.is_valid_fbc("fb.1.1612345678901.AbCdEfGhIjKlMnOpQrStUvWxYz")
        assert result is True

    def test_is_valid_fbc_incorrect_format(self, service):
        """Rejeita fbc com formato incorreto"""
        result = service.is_valid_fbc("invalid_fbc_value")
        assert result is False

    def test_is_valid_fbc_empty(self, service):
        """Rejeita fbc vazio"""
        result = service.is_valid_fbc("")
        assert result is False

    def test_is_valid_fbp_correct_format(self, service):
        """Valida fbp com formato correto"""
        result = service.is_valid_fbp("fb.1.1612345678901.1234567890")
        assert result is True

    def test_is_valid_fbp_incorrect_format(self, service):
        """Rejeita fbp com formato incorreto"""
        result = service.is_valid_fbp("invalid_fbp_value")
        assert result is False

    def test_is_valid_fbp_empty(self, service):
        """Rejeita fbp vazio"""
        result = service.is_valid_fbp("")
        assert result is False


class TestMetaCapiServiceSanitization:
    """Testes de sanitização de payload"""

    @pytest.fixture
    def service(self):
        """Cria instância do serviço com configuração mockada"""
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_sanitize_removes_invalid_custom_data_keys(self, service):
        """Remove chaves inválidas de custom_data"""
        event = {
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": "order_123",
            "action_source": "website",
            "user_data": {},
            "custom_data": {
                "value": 100.0,
                "currency": "BRL",
                "order_id": "123",
                # Campos inválidos que devem ser removidos
                "city": "Goiania",
                "state": "GO",
                "zip_code": "74000000",
                "latitude": -16.6799,
                "longitude": -49.2560,
            },
        }

        result = service.sanitize_event_payload(event)

        # Deve manter campos válidos
        assert result["custom_data"]["value"] == 100.0
        assert result["custom_data"]["currency"] == "BRL"
        assert result["custom_data"]["order_id"] == "123"

        # Deve remover campos inválidos de custom_data
        assert "city" not in result["custom_data"]
        assert "state" not in result["custom_data"]
        assert "zip_code" not in result["custom_data"]
        assert "latitude" not in result["custom_data"]
        assert "longitude" not in result["custom_data"]

        # Deve mover localização para user_data como hash
        assert "ct" in result["user_data"]  # city -> ct (hashed)
        assert "st" in result["user_data"]  # state -> st (hashed)
        assert "zp" in result["user_data"]  # zip_code -> zp (hashed)

    def test_sanitize_normalizes_future_event_time(self, service):
        """Normaliza event_time no futuro para agora"""
        future_time = int(time.time()) + 3600  # 1 hora no futuro

        event = {
            "event_name": "Purchase",
            "event_time": future_time,
            "event_id": "order_123",
            "action_source": "website",
            "user_data": {},
            "custom_data": {"value": 100.0, "currency": "BRL"},
        }

        result = service.sanitize_event_payload(event)

        # event_time não deve estar no futuro
        assert result["event_time"] <= int(time.time())

    def test_sanitize_normalizes_milliseconds_to_seconds(self, service):
        """Converte event_time de milissegundos para segundos"""
        now_millis = int(time.time() * 1000)  # Em milissegundos

        event = {
            "event_name": "Purchase",
            "event_time": now_millis,
            "event_id": "order_123",
            "action_source": "website",
            "user_data": {},
            "custom_data": {"value": 100.0, "currency": "BRL"},
        }

        result = service.sanitize_event_payload(event)

        # Deve estar em segundos (não milissegundos)
        assert result["event_time"] < 10_000_000_000

    def test_sanitize_removes_invalid_fbc(self, service):
        """Remove fbc inválido"""
        event = {
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": "order_123",
            "action_source": "website",
            "user_data": {"fbc": "invalid_fbc_value"},
            "custom_data": {"value": 100.0, "currency": "BRL"},
        }

        result = service.sanitize_event_payload(event)

        # fbc inválido deve ser removido
        assert "fbc" not in result["user_data"]

    def test_sanitize_keeps_valid_fbc(self, service):
        """Mantém fbc válido"""
        valid_fbc = "fb.1.1612345678901.AbCdEfGhIjKlMnOpQrStUvWxYz"

        event = {
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": "order_123",
            "action_source": "website",
            "user_data": {"fbc": valid_fbc},
            "custom_data": {"value": 100.0, "currency": "BRL"},
        }

        result = service.sanitize_event_payload(event)

        # fbc válido deve ser mantido
        assert result["user_data"]["fbc"] == valid_fbc

    def test_sanitize_preserves_event_source_url_and_client_ip(self, service):
        """Mantém campos úteis não-hashados usados pelo CAPI."""
        event = {
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": "order_123",
            "action_source": "website",
            "event_source_url": "https://lpb.planteumaflor.com/oferta",
            "user_data": {"client_ip_address": "203.0.113.10"},
            "custom_data": {"value": 100.0, "currency": "BRL"},
        }

        result = service.sanitize_event_payload(event)

        assert result["event_source_url"] == "https://lpb.planteumaflor.com/oferta"
        assert result["user_data"]["client_ip_address"] == "203.0.113.10"


class TestMetaCapiPurchaseEnrichment:
    """Testes de enriquecimento do Purchase com dados já disponíveis no sistema."""

    def test_build_purchase_event_enriches_with_lead_and_cliente(self, app):
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app import db
            from app.models.cliente import Cliente
            from app.models.lead import Lead
            from app.models.pedido import Pedido
            from app.services.meta_capi import MetaConversionsApiService

            with app.app_context():
                cliente = Cliente(
                    nome="Maria Flor",
                    telefone="62999990000",
                    email="Maria@Teste.com",
                )
                db.session.add(cliente)
                db.session.commit()

                lead = Lead(
                    dedup_key="lead-meta-1",
                    phone="62999990000",
                    fbclid="IwARabc123",
                    fbp="fb.1.1711111111111.555666777888",
                    ip_address="203.0.113.42",
                    url="https://lpb.planteumaflor.com/oferta?fbclid=IwARabc123",
                    created_at=datetime(2025, 1, 5, 12, 0, 0, tzinfo=timezone.utc),
                )
                db.session.add(lead)
                db.session.commit()

                pedido = Pedido(
                    cliente="Maria Flor",
                    telefone_cliente="(62) 99999-0000",
                    destinatario="Cliente Final",
                    tipo_pedido="Entrega",
                    produto="Buquê Premium",
                    valor="150,00",
                    dia_entrega=date.today(),
                    horario="10:00",
                    cidade="Goiânia",
                    cep="74000-000",
                    status="confirmado",
                    status_pagamento="Pago",
                    cliente_id=cliente.id,
                )
                db.session.add(pedido)
                db.session.commit()

                service = MetaConversionsApiService()
                event = service.build_purchase_event(pedido)
                expected_fbc = service.build_fbc_from_fbclid(
                    lead.fbclid, lead.created_at
                )

                assert event["event_name"] == "Purchase"
                assert event["event_source_url"] == lead.url
                assert event["user_data"]["fbp"] == lead.fbp
                assert event["user_data"]["fbc"] == expected_fbc
                assert event["user_data"]["client_ip_address"] == "203.0.113.42"
                assert event["user_data"]["em"] == [
                    service.hash_sha256(service.normalize_email("Maria@Teste.com"))
                ]
                assert event["user_data"]["external_id"] == [
                    service.hash_sha256(f"cliente:{cliente.id}")
                ]


class TestMetaCapiSourceFilter:
    def test_should_skip_site_and_nuvemshop(self, app):
        from app.models.pedido import Pedido
        from app.utils.meta_capi_helper import should_skip_purchase_for_meta_capi

        with app.app_context():
            pedido_site = Pedido(
                cliente="Cliente Site",
                telefone_cliente="62999990000",
                destinatario="Destinatário",
                tipo_pedido="Entrega",
                produto="Buquê",
                dia_entrega=date.today(),
                horario="10:00",
                cidade="Goiânia",
                status_pagamento="Pago",
                fonte_pedido="Site",
            )
            pedido_nuvemshop = Pedido(
                cliente="Cliente Nuvem",
                telefone_cliente="62999990001",
                destinatario="Destinatário",
                tipo_pedido="Entrega",
                produto="Buquê",
                dia_entrega=date.today(),
                horario="10:00",
                cidade="Goiânia",
                status_pagamento="Pago",
                plataforma="Nuvemshop",
            )
            pedido_fonte_nuvemshop = Pedido(
                cliente="Cliente Nuvem (fonte)",
                telefone_cliente="62999990003",
                destinatario="Destinatário",
                tipo_pedido="Entrega",
                produto="Buquê",
                dia_entrega=date.today(),
                horario="10:00",
                cidade="Goiânia",
                status_pagamento="Pago",
                fonte_pedido="Nuvemshop",
            )
            pedido_manual = Pedido(
                cliente="Cliente Manual",
                telefone_cliente="62999990002",
                destinatario="Destinatário",
                tipo_pedido="Entrega",
                produto="Buquê",
                dia_entrega=date.today(),
                horario="10:00",
                cidade="Goiânia",
                status_pagamento="Pago",
                fonte_pedido="WhatsApp",
            )

            assert should_skip_purchase_for_meta_capi(pedido_site) is True
            assert should_skip_purchase_for_meta_capi(pedido_nuvemshop) is True
            assert should_skip_purchase_for_meta_capi(pedido_fonte_nuvemshop) is True
            assert should_skip_purchase_for_meta_capi(pedido_manual) is False


class TestMetaCapiServiceErrorClassification:
    """Testes de classificação de erros"""

    @pytest.fixture
    def service(self):
        """Cria instância do serviço com configuração mockada"""
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_classify_error_rate_limit(self, service):
        """429 é retryable"""
        error_type, is_retryable = service.classify_error({}, 429)
        assert error_type == "retryable"
        assert is_retryable is True

    def test_classify_error_server_error(self, service):
        """5xx é retryable"""
        error_type, is_retryable = service.classify_error({}, 500)
        assert error_type == "retryable"
        assert is_retryable is True

    def test_classify_error_unauthorized(self, service):
        """401 é permanent"""
        error_type, is_retryable = service.classify_error({}, 401)
        assert error_type == "permanent"
        assert is_retryable is False

    def test_classify_error_forbidden(self, service):
        """403 é permanent"""
        error_type, is_retryable = service.classify_error({}, 403)
        assert error_type == "permanent"
        assert is_retryable is False

    def test_classify_error_bad_request_validation(self, service):
        """400 com validation é permanent"""
        response = {"error": {"message": "Validation error"}}
        error_type, is_retryable = service.classify_error(response, 400)
        assert error_type == "permanent"
        assert is_retryable is False

    def test_classify_error_configuration_error(self, service):
        """Erro de configuração é permanent"""
        response = {"_error": "META_PIXEL_ID deve estar configurado no .env"}
        error_type, is_retryable = service.classify_error(response, 0)
        assert error_type == "permanent"
        assert is_retryable is False


class TestMetaCapiServiceSendEvents:
    """Testes de envio de eventos (mockando requests)"""

    @pytest.fixture
    def service(self):
        """Cria instância do serviço com configuração mockada"""
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_send_events_without_credentials(self):
        """Retorna erro sem credenciais"""
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "",
                "META_CAPI_ACCESS_TOKEN": "",
            },
            clear=False,
        ):
            from app.services.meta_capi import MetaConversionsApiService

            service = MetaConversionsApiService()

            result = service.send_events([{"event_name": "Purchase"}])

            assert result["_status_code"] == 0
            assert "configurado" in result["_error"].lower()

    def test_send_events_empty_list(self, service):
        """Retorna sucesso para lista vazia"""
        result = service.send_events([])

        assert result["events_received"] == 0
        assert "Nenhum evento" in result.get("message", "")

    @patch("app.services.meta_capi.requests.post")
    def test_send_events_success(self, mock_post, service):
        """Envia eventos com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events_received": 1,
            "fbtrace_id": "abc123",
        }
        mock_post.return_value = mock_response

        events = [
            {
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "event_id": "order_123",
                "action_source": "website",
                "user_data": {"ph": ["hash123"]},
                "custom_data": {"value": 100.0, "currency": "BRL"},
            }
        ]

        result = service.send_events(events)

        assert result["events_received"] == 1
        assert result["fbtrace_id"] == "abc123"
        assert result["_status_code"] == 200

    @patch("app.services.meta_capi.requests.post")
    def test_send_events_failure(self, mock_post, service):
        """Trata erro de envio"""
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid parameter",
                "code": 100,
                "error_subcode": 2804016,
            }
        }

        error = HTTPError(response=mock_response)
        mock_post.side_effect = error

        events = [
            {
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "event_id": "order_123",
                "action_source": "website",
                "user_data": {},
                "custom_data": {"value": 100.0, "currency": "BRL"},
            }
        ]

        result = service.send_events(events)

        assert result["_status_code"] == 400
        assert "Invalid parameter" in result["_error"]


class TestMetaCapiOutboxRepository:
    """Testes do repositório de Outbox"""

    @pytest.fixture
    def app(self):
        """Cria aplicação Flask para testes"""
        import tempfile

        db_fd, db_path = tempfile.mkstemp()

        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test_pixel_123",
                "META_CAPI_ACCESS_TOKEN": "test_token_abc",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app import create_app, db

            app = create_app(
                config={
                    "TESTING": True,
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                    "SECRET_KEY": "test-secret-key",
                }
            )

            with app.app_context():
                db.create_all()
                yield app
                db.session.close()
                db.engine.dispose()
                db.drop_all()

        os.close(db_fd)
        try:
            os.unlink(db_path)
        except (PermissionError, FileNotFoundError):
            pass

    def _create_test_pedido(self, cliente="João Silva", telefone="62999887766"):
        """Helper para criar pedido de teste com todos os campos obrigatórios"""
        from datetime import date

        from app.models.pedido import Pedido

        return Pedido(
            cliente=cliente,
            telefone_cliente=telefone,
            destinatario="Destinatário Teste",
            tipo_pedido="Entrega",
            produto="Buquê de Rosas",
            dia_entrega=date.today(),
            horario="10:00",
            cidade="Goiania",
            status="confirmado",
            status_pagamento="Pago",
        )

    def test_create_from_pedido(self, app):
        """Cria outbox a partir de pedido"""
        from app import db
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            # Criar pedido de teste
            pedido = self._create_test_pedido()
            db.session.add(pedido)
            db.session.commit()

            # Criar outbox
            repo = MetaCapiOutboxRepository()
            outbox = repo.create_from_pedido(pedido)

            assert outbox is not None
            assert outbox.order_id == pedido.id
            assert outbox.event_id == f"order_{pedido.id}"
            assert outbox.status == "pending"
            assert outbox.attempts == 0

    def test_create_from_pedido_duplicate(self, app):
        """Não cria duplicata de outbox"""
        from app import db
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            # Criar pedido de teste
            pedido = self._create_test_pedido()
            db.session.add(pedido)
            db.session.commit()

            # Criar outbox
            repo = MetaCapiOutboxRepository()
            outbox1 = repo.create_from_pedido(pedido)
            outbox2 = repo.create_from_pedido(pedido)

            assert outbox1 is not None
            assert outbox2 is None  # Duplicata retorna None

    def test_create_outbox_if_purchase_envia_imediatamente_quando_ok(self, app):
        """Após criar outbox, tenta envio HTTP imediato (mock) e marca como sent."""
        from app import db
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository
        from app.utils.meta_capi_helper import create_outbox_if_purchase

        with app.app_context():
            pedido = self._create_test_pedido()
            db.session.add(pedido)
            db.session.commit()

            success_response = {"_status_code": 200, "events_received": 1, "fbtrace_id": "t1"}
            with patch(
                "app.services.meta_capi.MetaConversionsApiService.send_events",
                return_value=success_response,
            ):
                created = create_outbox_if_purchase(pedido, None, None)
                assert created is True

            ob = MetaCapiOutboxRepository().get_by_order_id(pedido.id)
            assert ob is not None
            assert ob.status == "sent"

    def test_create_from_pedido_skips_site_and_nuvemshop(self, app):
        """Não cria outbox para pedidos que já têm tracking próprio."""
        from app import db
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            pedido_site = self._create_test_pedido(cliente="Cliente Site", telefone="62999887760")
            pedido_site.fonte_pedido = "Site"

            pedido_nuvem = self._create_test_pedido(cliente="Cliente Nuvem", telefone="62999887761")
            pedido_nuvem.plataforma = "Nuvemshop"

            db.session.add_all([pedido_site, pedido_nuvem])
            db.session.commit()

            repo = MetaCapiOutboxRepository()

            assert repo.create_from_pedido(pedido_site) is None
            assert repo.create_from_pedido(pedido_nuvem) is None

    def test_get_pending(self, app):
        """Busca outbox pendentes"""
        from app import db
        from app.models.pedido import Pedido
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            # Criar pedidos de teste
            for i in range(3):
                pedido = self._create_test_pedido(
                    cliente=f"Cliente {i}",
                    telefone=f"6299988776{i}",
                )
                db.session.add(pedido)
            db.session.commit()

            # Criar outboxes
            repo = MetaCapiOutboxRepository()
            for pedido in Pedido.query.all():
                repo.create_from_pedido(pedido)

            # Buscar pendentes
            pending = repo.get_pending(limit=10)

            assert len(pending) == 3
            for entry in pending:
                assert entry.status == "pending"

    def test_mark_sent(self, app):
        """Marca outbox como enviado"""
        from app import db
        from app.models.pedido import datetime_now_brazil
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            # Criar pedido e outbox
            pedido = self._create_test_pedido()
            db.session.add(pedido)
            db.session.commit()

            repo = MetaCapiOutboxRepository()
            outbox = repo.create_from_pedido(pedido)

            # Marcar como enviado
            response = {"events_received": 1, "fbtrace_id": "test123"}
            updated = repo.mark_sent(outbox.id, datetime_now_brazil(), response)

            assert updated.status == "sent"
            assert updated.sent_at is not None
            assert "test123" in updated.last_error  # Debug info

    def test_mark_failed(self, app):
        """Marca outbox como falhou"""
        from app import db
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            # Criar pedido e outbox
            pedido = self._create_test_pedido()
            db.session.add(pedido)
            db.session.commit()

            repo = MetaCapiOutboxRepository()
            outbox = repo.create_from_pedido(pedido)

            # Marcar como falhou
            updated = repo.mark_failed(
                outbox.id,
                error="Invalid parameter",
                status_code=400,
                error_type="permanent",
                attempts=1,
            )

            assert updated.status == "failed"
            assert updated.error_type == "permanent"
            assert updated.attempts == 1
            assert "400" in updated.last_error

    def test_get_failed_retryable(self, app):
        """Busca outbox failed retryable"""
        from app import db
        from app.models.pedido import Pedido
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        with app.app_context():
            # Criar pedidos
            for i in range(3):
                pedido = self._create_test_pedido(
                    cliente=f"Cliente {i}",
                    telefone=f"6299988776{i}",
                )
                db.session.add(pedido)
            db.session.commit()

            # Criar outboxes e marcar alguns como failed
            repo = MetaCapiOutboxRepository()
            outboxes = []
            for pedido in Pedido.query.all():
                outbox = repo.create_from_pedido(pedido)
                outboxes.append(outbox)

            # Marcar primeiro como retryable (deve aparecer)
            repo.mark_failed(outboxes[0].id, "Rate limit", 429, "retryable", 1)
            # Marcar segundo como permanent (não deve aparecer)
            repo.mark_failed(outboxes[1].id, "Invalid", 400, "permanent", 1)
            # Terceiro continua pending

            # Buscar failed retryable
            failed_retryable = repo.get_failed_retryable(limit=10)

            assert len(failed_retryable) == 1
            assert failed_retryable[0].id == outboxes[0].id
            assert failed_retryable[0].error_type == "retryable"


def test_meta_capi_verbose_summary():
    """Resumo verbose para inspeção manual com pytest -s."""
    with patch.dict(
        os.environ,
        {
            "META_PIXEL_ID": "test_pixel_123",
            "META_CAPI_ACCESS_TOKEN": "test_token_abc",
            "META_CAPI_USE_GATEWAY": "false",
        },
    ):
        from app.services.meta_capi import MetaConversionsApiService

        service = MetaConversionsApiService()

        normalized_phone = service.normalize_phone_br_e164("(62) 99988-7766")
        normalized_fn = service.normalize_fn("João Silva")
        hashed_fn = service.hash_sha256(normalized_fn)
        valid_fbc = "fb.1.1612345678901.AbCdEfGhIjKlMnOpQrStUvWxYz"
        valid_fbp = "fb.1.1612345678901.1234567890"

        event = {
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": "order_verbose_1",
            "action_source": "website",
            "user_data": {"fbc": valid_fbc, "fbp": valid_fbp},
            "custom_data": {
                "value": 100.0,
                "currency": "BRL",
                "city": "Goiania",
                "state": "GO",
                "zip_code": "74000000",
            },
        }
        sanitized = service.sanitize_event_payload(event)
        retryable = service.classify_error({}, 429)
        permanent = service.classify_error({}, 401)

        print("=== META CAPI VERBOSE SUMMARY ===")
        print(f"normalized_phone={normalized_phone}")
        print(f"normalized_fn={normalized_fn}")
        print(f"hashed_fn_prefix={hashed_fn[:12]}")
        print(f"is_valid_fbc={service.is_valid_fbc(valid_fbc)}")
        print(f"is_valid_fbp={service.is_valid_fbp(valid_fbp)}")
        print(f"sanitized_user_data_keys={sorted(sanitized.get('user_data', {}).keys())}")
        print(f"classify_429={retryable}")
        print(f"classify_401={permanent}")

        assert normalized_phone == "+5562999887766"
        assert normalized_fn == "joao"
        assert len(hashed_fn) == 64
        assert service.is_valid_fbc(valid_fbc) is True
        assert service.is_valid_fbp(valid_fbp) is True
        assert "ct" in sanitized["user_data"]
        assert retryable == ("retryable", True)
        assert permanent == ("permanent", False)


class TestFbcMilliseconds:
    """Garante que o fbc sai em milissegundos quando a flag está ligada."""

    @pytest.fixture
    def service(self):
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test",
                "META_CAPI_ACCESS_TOKEN": "t",
                "META_CAPI_USE_GATEWAY": "false",
                "META_CAPI_FBC_MS_ENABLED": "true",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_build_fbc_uses_milliseconds(self, service):
        with patch.dict(os.environ, {"META_CAPI_FBC_MS_ENABLED": "true"}):
            fbc = service.build_fbc_from_fbclid("abc123")
            assert fbc is not None
            ts = int(fbc.split(".")[2])
            assert ts >= 10**12, f"timestamp deve ser ms, veio {ts}"

    def test_build_fbc_from_datetime_source_uses_ms(self, service):
        with patch.dict(os.environ, {"META_CAPI_FBC_MS_ENABLED": "true"}):
            dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            fbc = service.build_fbc_from_fbclid("abc", timestamp_source=dt)
            ts = int(fbc.split(".")[2])
            assert ts == int(dt.timestamp() * 1000)

    def test_is_valid_fbc_rejects_seconds_when_flag_on(self, service):
        with patch.dict(os.environ, {"META_CAPI_FBC_MS_ENABLED": "true"}):
            assert service.is_valid_fbc("fb.1.1700000000.abc") is False
            assert service.is_valid_fbc("fb.1.1700000000000.abc") is True

    def test_is_valid_fbc_accepts_seconds_when_flag_off(self, service):
        with patch.dict(os.environ, {"META_CAPI_FBC_MS_ENABLED": "false"}):
            assert service.is_valid_fbc("fb.1.1700000000.abc") is True


class TestPurchaseSkipInvalidValue:
    """Skip silencioso de Purchase quando `total_pago` é inválido."""

    @pytest.fixture
    def service(self):
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test",
                "META_CAPI_ACCESS_TOKEN": "t",
                "META_CAPI_USE_GATEWAY": "false",
                "META_CAPI_SKIP_INVALID_PURCHASE": "true",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def _make_pedido(self, total_pago_value):
        pedido = MagicMock()
        pedido.id = 42
        pedido.telefone_cliente = "62999887766"
        pedido.cliente = "Joao"
        pedido.fonte_pedido = "WhatsApp"
        pedido.fonte_pedido_rel = None
        pedido.valor = ""
        pedido.cidade = "Goiania"
        pedido.cep = "74000000"
        pedido.tipo_pedido = "Entrega"
        pedido.cliente_id = None
        pedido.cliente_rel = None
        pedido.fbc = None
        pedido.fbp = None
        pedido.updated_at = datetime.now()
        pedido.created_at = datetime.now()
        pedido.total_pago = MagicMock(return_value=total_pago_value)
        return pedido

    def test_returns_none_when_value_zero(self, service):
        with patch.dict(os.environ, {"META_CAPI_SKIP_INVALID_PURCHASE": "true"}), \
            patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido(0.0)
            assert service.build_purchase_event(pedido) is None

    def test_returns_none_when_value_below_min(self, service):
        with patch.dict(os.environ, {"META_CAPI_SKIP_INVALID_PURCHASE": "true"}), \
            patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido(0.01)
            assert service.build_purchase_event(pedido) is None

    def test_returns_event_when_value_valid(self, service):
        with patch.dict(os.environ, {"META_CAPI_SKIP_INVALID_PURCHASE": "true"}), \
            patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido(150.0)
            event = service.build_purchase_event(pedido)
            assert event is not None
            assert event["custom_data"]["value"] == 150.0

    def test_flag_off_does_not_skip(self, service):
        """Sem a flag, builder devolve evento (mesmo com value=0).

        Regressão: o código legado tinha um fallback `valor_total = 0.01`
        que nunca chegava ao payload (custom_data era montado antes). Não
        replicamos esse bug — apenas garantimos que a flag-off não introduz
        skip, mantendo o comportamento histórico.
        """
        with patch.dict(os.environ, {"META_CAPI_SKIP_INVALID_PURCHASE": "false"}), \
            patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido(0.0)
            event = service.build_purchase_event(pedido)
            assert event is not None
            # value sai como veio (0.0) — flag-off não corrige nada
            assert event["custom_data"]["value"] == 0.0


class TestValueResolver:
    """resolve_value busca por utm_content, com fallback para default."""

    def setup_method(self, _method):
        from app.utils.meta_capi_value_resolver import reset_cache_for_tests

        reset_cache_for_tests()

    def teardown_method(self, _method):
        from app.utils.meta_capi_value_resolver import reset_cache_for_tests

        reset_cache_for_tests()

    def test_known_utm_returns_mapped_value(self):
        from app.utils.meta_capi_value_resolver import resolve_value

        lead = MagicMock(utm_content="CARRO|HIGH-TCK", utm_campaign=None)
        assert resolve_value(lead, "contact") == 25.0
        assert resolve_value(lead, "lead") == 125.0

    def test_utm_content_is_case_insensitive(self):
        from app.utils.meta_capi_value_resolver import resolve_value

        lead = MagicMock(utm_content="carro|low-tck", utm_campaign=None)
        assert resolve_value(lead, "contact") == 8.0

    def test_unknown_utm_uses_default(self):
        from app.utils.meta_capi_value_resolver import resolve_value

        lead = MagicMock(utm_content="UNKNOWN|UTM", utm_campaign=None)
        assert resolve_value(lead, "contact") == 10.0
        assert resolve_value(lead, "lead") == 50.0

    def test_missing_utm_uses_default(self):
        from app.utils.meta_capi_value_resolver import resolve_value

        lead = MagicMock(utm_content=None, utm_campaign=None)
        assert resolve_value(lead, "contact") == 10.0

    def test_falls_back_to_utm_campaign(self):
        from app.utils.meta_capi_value_resolver import resolve_value

        lead = MagicMock(utm_content=None, utm_campaign="URGENCIA|DATAS")
        assert resolve_value(lead, "lead") == 75.0


class TestExternalIdsArray:
    """external_id como array por evento, com identificadores múltiplos."""

    @pytest.fixture
    def service(self):
        with patch.dict(
            os.environ,
            {
                "META_PIXEL_ID": "test",
                "META_CAPI_ACCESS_TOKEN": "t",
                "META_CAPI_USE_GATEWAY": "false",
            },
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_contact_uses_lead_id_and_fbp(self, service):
        lead = MagicMock(id=7, fbp="fb.1.123.456", fbclid="abc", phone=None)
        ids = service.build_external_ids_for_event("Contact", lead=lead)
        assert len(ids) == 3
        assert all(len(h) == 64 for h in ids)
        # Determinístico: hash de "lead:7" estável
        assert service.hash_sha256("lead:7") in ids
        assert service.hash_sha256("fbp:fb.1.123.456") in ids

    def test_lead_includes_phone_hash(self, service):
        lead = MagicMock(id=7, fbp=None, fbclid=None, phone="62999887766")
        ids = service.build_external_ids_for_event("Lead", lead=lead)
        assert service.hash_sha256("lead:7") in ids
        assert service.hash_sha256("phone:+5562999887766") in ids

    def test_purchase_uses_phone_and_cliente(self, service):
        lead = MagicMock(id=7, fbp=None, fbclid=None, phone="62999887766")
        pedido = MagicMock(
            id=99, telefone_cliente="62999887766", cliente_id=42
        )
        ids = service.build_external_ids_for_event("Purchase", lead=lead, pedido=pedido)
        assert service.hash_sha256("phone:+5562999887766") in ids
        assert service.hash_sha256("cliente:42") in ids
        assert service.hash_sha256("lead:7") in ids

    def test_purchase_falls_back_to_order_id(self, service):
        pedido = MagicMock(
            id=99, telefone_cliente="invalid", cliente_id=None
        )
        ids = service.build_external_ids_for_event("Purchase", lead=None, pedido=pedido)
        assert service.hash_sha256("order:99") in ids

    def test_contact_shares_lead_hash_with_lead_event(self, service):
        """Cross-event matching: Contact e Lead do mesmo lead compartilham lead:{id}."""
        lead = MagicMock(id=7, fbp="fb.1.1.2", fbclid=None, phone="62999887766")
        contact_ids = set(service.build_external_ids_for_event("Contact", lead=lead))
        lead_ids = set(service.build_external_ids_for_event("Lead", lead=lead))
        intersection = contact_ids & lead_ids
        assert service.hash_sha256("lead:7") in intersection


class TestNormalizeLastName:
    """Split de nome completo para `ln` (Meta usa como matching signal forte)."""

    @pytest.fixture
    def service(self):
        with patch.dict(
            os.environ,
            {"META_PIXEL_ID": "t", "META_CAPI_ACCESS_TOKEN": "t", "META_CAPI_USE_GATEWAY": "false"},
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def test_single_token_returns_empty(self, service):
        assert service.normalize_ln("Maria") == ""

    def test_two_tokens_returns_last(self, service):
        assert service.normalize_ln("Maria Silva") == "silva"

    def test_multi_tokens_returns_all_after_first(self, service):
        assert service.normalize_ln("Maria da Silva") == "da silva"

    def test_accents_stripped(self, service):
        assert service.normalize_ln("João Conceição") == "conceicao"

    def test_empty_input(self, service):
        assert service.normalize_ln("") == ""
        assert service.normalize_ln(None) == ""


class TestPurchaseEnrichmentLnAndUa:
    """Purchase event inclui ln (split de cliente) e client_user_agent (do lead)."""

    @pytest.fixture
    def service(self):
        with patch.dict(
            os.environ,
            {"META_PIXEL_ID": "t", "META_CAPI_ACCESS_TOKEN": "t", "META_CAPI_USE_GATEWAY": "false"},
        ):
            from app.services.meta_capi import MetaConversionsApiService

            return MetaConversionsApiService()

    def _make_pedido(self, cliente_name="Maria da Silva"):
        pedido = MagicMock()
        pedido.id = 99
        pedido.telefone_cliente = "62999887766"
        pedido.cliente = cliente_name
        pedido.fonte_pedido = "WhatsApp"
        pedido.fonte_pedido_rel = None
        pedido.valor = "150,00"
        pedido.cidade = "Goiania"
        pedido.cep = "74000000"
        pedido.tipo_pedido = "Entrega"
        pedido.cliente_id = None
        pedido.cliente_rel = None
        pedido.fbc = None
        pedido.fbp = None
        pedido.updated_at = datetime.now()
        pedido.created_at = datetime.now()
        pedido.total_pago = MagicMock(return_value=150.0)
        return pedido

    def _make_lead(self, ua="Mozilla/5.0 (Linux; Android 13) Chrome/120"):
        lead = MagicMock()
        lead.id = 7
        lead.fbclid = None
        lead.fbp = None
        lead.created_at = datetime.now()
        lead.ip_address = "1.2.3.4"
        lead.client_user_agent = ua
        lead.url = None
        return lead

    def test_purchase_includes_ln_when_compound_name(self, service):
        with patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido("Maria da Silva")
            event = service.build_purchase_event(pedido)
            assert "ln" in event["user_data"]
            assert event["user_data"]["ln"] == [service.hash_sha256("da silva")]
            assert event["user_data"]["fn"] == [service.hash_sha256("maria")]

    def test_purchase_omits_ln_when_single_name(self, service):
        with patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido("Maria")
            event = service.build_purchase_event(pedido)
            assert "ln" not in event["user_data"]
            assert "fn" in event["user_data"]

    def test_purchase_copies_ua_from_lead(self, service):
        lead = self._make_lead("CustomUA/1.0")
        with patch.object(service, "resolve_lead_for_purchase", return_value=lead):
            pedido = self._make_pedido()
            event = service.build_purchase_event(pedido)
            assert event["user_data"]["client_user_agent"] == "CustomUA/1.0"

    def test_purchase_truncates_ua_at_512(self, service):
        lead = self._make_lead("x" * 1000)
        with patch.object(service, "resolve_lead_for_purchase", return_value=lead):
            pedido = self._make_pedido()
            event = service.build_purchase_event(pedido)
            assert len(event["user_data"]["client_user_agent"]) == 512

    def test_purchase_omits_ua_when_no_lead(self, service):
        with patch.object(service, "resolve_lead_for_purchase", return_value=None):
            pedido = self._make_pedido()
            event = service.build_purchase_event(pedido)
            assert "client_user_agent" not in event["user_data"]
