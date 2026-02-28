# -*- coding: utf-8 -*-
"""
Testes para DistanciaService — cache via EnderecoCliente e integração Google.
Todas as chamadas HTTP são mockadas.
"""
from unittest.mock import MagicMock, patch

from app import db
from app.models.cliente import Cliente
from app.models.endereco_cliente import EnderecoCliente
from app.services.distancia import DistanciaService

# ── _check_endereco_cache ─────────────────────────────────────────────


def test_check_cache_returns_none_without_cliente_id(app):
    with app.app_context():
        result = DistanciaService._check_endereco_cache(None, rua="Rua X", bairro="Y")
        assert result is None


def test_check_cache_returns_none_when_no_match(app):
    with app.app_context():
        cliente = Cliente(nome="NoCache", telefone="62900000000")
        db.session.add(cliente)
        db.session.commit()

        result = DistanciaService._check_endereco_cache(
            cliente.id, rua="Rua Inexistente", bairro="Bairro X"
        )
        assert result is None


def test_check_cache_returns_coords_when_cached(app):
    with app.app_context():
        cliente = Cliente(nome="CacheHit", telefone="62911111111")
        db.session.add(cliente)
        db.session.commit()

        ec = EnderecoCliente(
            cliente_id=cliente.id,
            rua="Rua 10",
            numero="50",
            bairro="Centro",
            cidade="Goiânia",
            estado="GO",
        )
        ec.update_geocode_cache(lat=-16.70, lng=-49.25, confidence_status="AUTO_OK")
        db.session.add(ec)
        db.session.commit()

        result = DistanciaService._check_endereco_cache(
            cliente.id, rua="Rua 10", numero="50", bairro="Centro", cidade="Goiânia", cep=""
        )
        assert result is not None
        assert result["lat"] == -16.70
        assert result["lng"] == -49.25
        assert result["confidence_status"] == "AUTO_OK"


# ── _save_endereco_cache ─────────────────────────────────────────────


def test_save_cache_noop_without_cliente_id(app):
    """Não deve falhar quando cliente_id é None."""
    with app.app_context():
        # Não deve levantar exceção
        DistanciaService._save_endereco_cache(None, lat=-16.70, lng=-49.25, rua="Rua A", bairro="B")


def test_save_cache_updates_existing_endereco(app):
    with app.app_context():
        cliente = Cliente(nome="SaveCache", telefone="62922222222")
        db.session.add(cliente)
        db.session.commit()

        ec = EnderecoCliente(
            cliente_id=cliente.id,
            rua="Rua 20",
            numero="100",
            bairro="Setor Norte",
            cidade="Goiânia",
            estado="GO",
        )
        db.session.add(ec)
        db.session.commit()

        DistanciaService._save_endereco_cache(
            cliente.id,
            lat=-16.65,
            lng=-49.30,
            rua="Rua 20",
            numero="100",
            bairro="Setor Norte",
            cidade="Goiânia",
            cep="",
        )

        # Verificar que foi salvo
        updated = EnderecoCliente.query.get(ec.id)
        assert updated.lat == -16.65
        assert updated.lng == -49.30
        assert updated.geocode_provider == "google"
        assert updated.address_hash is not None


# ── _geocodificar_google ──────────────────────────────────────────────


@patch("app.services.google_geocoding.requests.get")
def test_geocodificar_google_success(mock_get, app):
    with app.app_context():
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {"lat": -16.69, "lng": -49.26},
                        "location_type": "ROOFTOP",
                    },
                    "place_id": "ChIJtest",
                    "formatted_address": "Rua 132, Goiânia",
                }
            ],
        }
        mock_get.return_value = mock_resp

        # Configurar API key na instância global (já instanciada no import)
        from app.services.google_geocoding import google_geocoding_service

        old_key = google_geocoding_service.api_key
        google_geocoding_service.api_key = "fake-key"
        google_geocoding_service.DEBUG = False

        try:
            svc = DistanciaService()
            svc.DEBUG = False
            result = svc._geocodificar_google("Rua 132, Goiânia, GO")
            assert result is not None
            assert result == (-49.26, -16.69)  # (lon, lat)
        finally:
            google_geocoding_service.api_key = old_key


# ── calcular_distancia_pedido com cache ───────────────────────────────


@patch.object(
    DistanciaService,
    "coords_floricultura",
    new_callable=lambda: property(lambda self: (-49.2648, -16.6869)),
)
@patch.object(DistanciaService, "_calcular_distancia_haversine")
def test_calcular_distancia_pedido_uses_cache(mock_haversine, mock_coords, app):
    """Quando há cache, não deve chamar geocodificação."""
    with app.app_context():
        cliente = Cliente(nome="CachePedido", telefone="62933333333")
        db.session.add(cliente)
        db.session.commit()

        ec = EnderecoCliente(
            cliente_id=cliente.id,
            rua="Rua Cache",
            numero="77",
            bairro="Setor Cache",
            cidade="Goiânia",
            estado="GO",
        )
        ec.update_geocode_cache(lat=-16.72, lng=-49.23, confidence_status="AUTO_OK")
        db.session.add(ec)
        db.session.commit()

        mock_haversine.return_value = {
            "distancia_km": 5.0,
            "duracao_min": 7.5,
            "coords_origem": (-49.2648, -16.6869),
            "coords_destino": (-49.23, -16.72),
            "metodo": "haversine",
        }

        svc = DistanciaService()
        svc.DEBUG = False

        with patch.object(svc, "geocodificar") as mock_geo:
            result = svc.calcular_distancia_pedido(
                pedido_id=999,
                rua="Rua Cache",
                numero="77",
                bairro="Setor Cache",
                cidade="Goiânia",
                cep="",
                cliente_id=cliente.id,
            )
            # geocodificar NÃO deve ser chamado quando cache hit
            mock_geo.assert_not_called()

        assert "error" not in result
        assert result["distancia_km"] == 5.0
