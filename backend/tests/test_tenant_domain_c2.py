"""Fase C.2 — isolamento de clientes, endereços e fontes."""

from datetime import date

from app import db
from app.models.cliente import Cliente
from app.models.endereco_cliente import EnderecoCliente
from app.models.fonte_pedido import FontePedido
from app.models.pedido import Pedido
from app.models.store import Store
from app.models.user import User
from app.services.auth_service import generate_token, hash_password
from scripts.migrations.add_store_ref_to_customers_and_sources import migrate


def _store(slug: str) -> Store:
    store = Store(name=slug, slug=slug, active=True)
    db.session.add(store)
    db.session.commit()
    return store


def _admin(store: Store, email: str) -> User:
    user = User(
        name=email,
        email=email,
        password_hash=hash_password("secret123"),
        role="admin",
        store_ref_id=store.id,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _headers(user: User, store: Store) -> dict[str, str]:
    return {"Authorization": f"Bearer {generate_token(user, store)}"}


def test_phone_and_source_name_are_unique_per_store(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        db.session.add_all(
            [
                Cliente(store_ref_id=store_a.id, nome="A", telefone="11999999999"),
                Cliente(store_ref_id=store_b.id, nome="B", telefone="11999999999"),
                FontePedido(store_ref_id=store_a.id, nome="Site"),
                FontePedido(store_ref_id=store_b.id, nome="Site"),
            ]
        )
        db.session.commit()
        assert Cliente.query.execution_options(include_all_tenants=True).count() == 2
        assert FontePedido.query.execution_options(include_all_tenants=True).count() == 2


def test_foreign_customer_address_and_source_are_not_visible(client, session):
    store_a = _store("a")
    store_b = _store("b")
    admin_a = _admin(store_a, "a@example.test")
    customer_b = Cliente(store_ref_id=store_b.id, nome="B", telefone="11999999999")
    source_b = FontePedido(store_ref_id=store_b.id, nome="Site")
    db.session.add_all([customer_b, source_b])
    db.session.flush()
    address_b = EnderecoCliente(
        store_ref_id=store_b.id,
        cliente_id=customer_b.id,
        rua="Rua B",
    )
    db.session.add(address_b)
    db.session.commit()

    headers = _headers(admin_a, store_a)
    assert client.get(f"/api/clientes/{customer_b.id}", headers=headers).status_code == 404
    assert (
        client.put(
            f"/api/clientes/enderecos/{address_b.id}",
            headers=headers,
            json={"rua": "tentativa"},
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/fontes-pedido/{source_b.id}",
            headers=headers,
            json={"nome": "tentativa"},
        ).status_code
        == 404
    )


def test_source_report_reads_pedidos_table_with_local_number(client, session):
    store = _store("default")
    admin = _admin(store, "admin@example.test")
    source = FontePedido(store_ref_id=store.id, nome="WhatsApp")
    db.session.add(source)
    db.session.flush()
    pedido = Pedido(
        store_ref_id=store.id,
        numero_pedido=42,
        fonte_pedido_id=source.id,
        cliente="Cliente",
        telefone_cliente="11999999999",
        destinatario="Destino",
        produto="Flores",
        valor="R$ 50,00",
        dia_entrega=date.today(),
        horario="10:00",
    )
    db.session.add(pedido)
    db.session.commit()

    headers = _headers(admin, store)
    listed = client.get(f"/api/pedidos/fonte/{source.id}", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["pedidos"][0]["numero_sequencial"] == 42

    stats = client.get(f"/api/pedidos/fonte/{source.id}/consolidado", headers=headers)
    payload = stats.get_json()
    assert payload["tabela"] == "pedidos"
    assert payload["estatisticas"] == {
        "total_pedidos": 1,
        "total_vendas": 50.0,
        "ultimo_numero": 42,
    }


def test_c2_migration_is_idempotent_on_fresh_schema(app):
    with app.app_context():
        store = _store("default")
        customer = Cliente(store_ref_id=store.id, nome="A", telefone="1")
        source = FontePedido(store_ref_id=store.id, nome="Site")
        db.session.add_all([customer, source])
        db.session.flush()
        db.session.add(EnderecoCliente(store_ref_id=store.id, cliente_id=customer.id, rua="Rua"))
        db.session.commit()

        migrate()
        migrate()

        assert Cliente.query.count() == 1
        assert FontePedido.query.count() == 1
        assert EnderecoCliente.query.count() == 1
