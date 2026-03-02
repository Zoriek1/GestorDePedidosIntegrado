# -*- coding: utf-8 -*-
"""
Testes para EnderecoCliente (campos de geocodificação, canonical, hash, cache).
"""
import hashlib

from app import db
from app.models.cliente import Cliente
from app.models.endereco_cliente import EnderecoCliente

# ── build_address_canonical ───────────────────────────────────────────


def test_canonical_full_address(app):
    with app.app_context():
        ec = EnderecoCliente(
            cliente_id=1,
            rua="Rua 132",
            numero="289",
            bairro="Setor Sul",
            cidade="Goiânia",
            estado="GO",
            cep="74093-210",
        )
        canonical = ec.build_address_canonical()
        assert "Rua 132" in canonical
        assert "289" in canonical
        assert "Setor Sul" in canonical
        assert "Goiânia - GO" in canonical
        assert "74093-210" in canonical
        assert canonical.endswith(", Brasil")


def test_canonical_without_numero(app):
    with app.app_context():
        ec = EnderecoCliente(
            cliente_id=1,
            rua="Avenida Goiás",
            numero="",
            bairro="Centro",
            cidade="Goiânia",
            estado="GO",
        )
        canonical = ec.build_address_canonical()
        assert "Avenida Goiás" in canonical
        assert "Centro" in canonical
        assert "Goiânia - GO" in canonical
        # Sem número, não deve ter separador vazio
        assert ",  " not in canonical


def test_canonical_defaults_cidade_estado(app):
    with app.app_context():
        ec = EnderecoCliente(
            cliente_id=1,
            rua="Rua X",
            numero="10",
            bairro="Setor Y",
        )
        canonical = ec.build_address_canonical()
        assert "Goiânia - GO" in canonical  # defaults


def test_canonical_cep_only_digits(app):
    with app.app_context():
        ec = EnderecoCliente(
            cliente_id=1,
            rua="Rua Z",
            numero="5",
            bairro="Bairro W",
            cep="74000100",  # sem hífen
        )
        canonical = ec.build_address_canonical()
        assert "74000-100" in canonical  # formatado


def test_canonical_invalid_cep_ignored(app):
    with app.app_context():
        ec = EnderecoCliente(
            cliente_id=1,
            rua="Rua A",
            numero="1",
            bairro="B",
            cep="123",  # inválido
        )
        canonical = ec.build_address_canonical()
        assert "123" not in canonical  # CEP inválido ignorado


# ── compute_address_hash ──────────────────────────────────────────────


def test_hash_is_sha256(app):
    with app.app_context():
        ec = EnderecoCliente(cliente_id=1, rua="Rua 1", numero="10", bairro="Centro")
        h = ec.compute_address_hash()
        assert len(h) == 64  # SHA-256 hex
        # Verificar manualmente
        canonical = ec.build_address_canonical()
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert h == expected


def test_hash_changes_when_address_changes(app):
    with app.app_context():
        ec = EnderecoCliente(cliente_id=1, rua="Rua 1", numero="10", bairro="Centro")
        hash1 = ec.compute_address_hash()

        ec.rua = "Rua 2"
        hash2 = ec.compute_address_hash()

        assert hash1 != hash2


def test_hash_stable_for_same_data(app):
    with app.app_context():
        ec1 = EnderecoCliente(cliente_id=1, rua="Rua A", numero="5", bairro="Setor B")
        ec2 = EnderecoCliente(cliente_id=99, rua="Rua A", numero="5", bairro="Setor B")
        # Mesmo endereço, cliente_id diferente → mesmo hash
        assert ec1.compute_address_hash() == ec2.compute_address_hash()


# ── needs_geocoding ──────────────────────────────────────────────────


def test_needs_geocoding_when_no_lat(app):
    with app.app_context():
        ec = EnderecoCliente(cliente_id=1, rua="Rua X", numero="1", bairro="Y")
        assert ec.needs_geocoding() is True


def test_needs_geocoding_after_cache(app):
    with app.app_context():
        ec = EnderecoCliente(cliente_id=1, rua="Rua X", numero="1", bairro="Y")
        ec.update_geocode_cache(lat=-16.68, lng=-49.26, confidence_status="AUTO_OK")
        assert ec.needs_geocoding() is False


def test_needs_geocoding_when_address_changed(app):
    with app.app_context():
        ec = EnderecoCliente(cliente_id=1, rua="Rua X", numero="1", bairro="Y")
        ec.update_geocode_cache(lat=-16.68, lng=-49.26)
        # Mudar endereço
        ec.rua = "Rua Z"
        assert ec.needs_geocoding() is True


# ── update_geocode_cache ──────────────────────────────────────────────


def test_update_geocode_cache_sets_all_fields(app):
    with app.app_context():
        ec = EnderecoCliente(cliente_id=1, rua="Rua Test", numero="100", bairro="Centro")
        ec.update_geocode_cache(
            lat=-16.70,
            lng=-49.25,
            location_type="ROOFTOP",
            place_id="ChIJtest",
            confidence_status="AUTO_OK",
            provider="google",
        )
        assert ec.lat == -16.70
        assert ec.lng == -49.25
        assert ec.location_type == "ROOFTOP"
        assert ec.place_id == "ChIJtest"
        assert ec.confidence_status == "AUTO_OK"
        assert ec.geocode_provider == "google"
        assert ec.address_canonical is not None
        assert ec.address_hash is not None
        assert ec.last_geocoded_at is not None


# ── to_dict inclui campos de geocoding ────────────────────────────────


def test_to_dict_includes_geocoding_fields(app):
    with app.app_context():
        ec = EnderecoCliente(
            cliente_id=1,
            rua="Rua T",
            numero="5",
            bairro="B",
            lat=-16.69,
            lng=-49.27,
            confidence_status="OK_WITH_CAUTION",
        )
        d = ec.to_dict()
        assert d["lat"] == -16.69
        assert d["lng"] == -49.27
        assert d["confidence_status"] == "OK_WITH_CAUTION"


# ── Persistência em banco (integração leve) ──────────────────────────


def test_persist_endereco_with_geocode(app):
    """Testa criação e persistência do EnderecoCliente com campos de geocoding."""
    with app.app_context():
        # Criar cliente primeiro (FK)
        cliente = Cliente(nome="Teste Geocode", telefone="62999990000")
        db.session.add(cliente)
        db.session.commit()

        ec = EnderecoCliente(
            cliente_id=cliente.id,
            rua="Rua 132",
            numero="289",
            bairro="Setor Sul",
            cidade="Goiânia",
            estado="GO",
            cep="74093210",
        )
        ec.update_geocode_cache(
            lat=-16.6869,
            lng=-49.2648,
            location_type="ROOFTOP",
            place_id="ChIJpersist",
            confidence_status="AUTO_OK",
        )
        db.session.add(ec)
        db.session.commit()

        # Buscar de volta
        found = EnderecoCliente.query.filter_by(
            cliente_id=cliente.id, address_hash=ec.address_hash
        ).first()
        assert found is not None
        assert found.lat == -16.6869
        assert found.lng == -49.2648
        assert found.confidence_status == "AUTO_OK"
        assert found.geocode_provider == "google"
