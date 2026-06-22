from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.integrations.bling.errors import BlingValidationError
from app.integrations.bling.mapper import BlingOrderMapper, parse_decimal_money


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("R$ 189,90", Decimal("189.90")),
        ("189,90", Decimal("189.90")),
        (189.90, Decimal("189.90")),
        ("1.234,56", Decimal("1234.56")),
        (None, Decimal("0.00")),
    ],
)
def test_parse_decimal_money(raw, expected):
    assert parse_decimal_money(raw) == expected


def test_delivery_label_includes_normalized_uf():
    pedido = SimpleNamespace(
        tipo_pedido="Entrega",
        destinatario="Gabriela",
        cliente="Maria",
        rua="Rua 13",
        numero="145",
        complemento="2701",
        apto=None,
        cidade="Goiânia",
        uf="GO",
        cep="74810-170",
        bairro="Jardim Goiás",
    )
    etiqueta = BlingOrderMapper()._etiqueta_entrega(pedido)
    assert etiqueta["uf"] == "GO"


def make_pedido(**overrides):
    data = {
        "id": 42,
        "valor": Decimal("200.00"),
        "status_pagamento": "Pendente",
        "pagamento": "Pix",
        "dia_entrega": date(2026, 7, 10),
        "created_at": datetime(2026, 6, 21, 9, 30),
        "paid_at": None,
        "valor_entrada": None,
        "valor_restante": None,
        "forma_pagamento_entrada": None,
        "forma_pagamento_restante": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_financial_plan_pago_settles_single_parcel_on_purchase_date():
    mapper = BlingOrderMapper()
    pedido = make_pedido(status_pagamento="Pago", pagamento="Pix")

    plan = mapper.build_financial_plan(pedido, Decimal("200.00"))

    assert plan == [
        {
            "kind": "PAGO",
            "marker": "GESTOR-42-PAGO",
            "amount": Decimal("200.00"),
            "due_date": "2026-06-21",
            "payment_label": "Pix",
            "should_settle": True,
        }
    ]


def test_financial_plan_pendente_due_on_delivery_date():
    mapper = BlingOrderMapper()
    pedido = make_pedido(status_pagamento="Pendente", pagamento="Boleto")

    plan = mapper.build_financial_plan(pedido, Decimal("200.00"))

    assert plan[0]["kind"] == "PENDENTE"
    assert plan[0]["marker"] == "GESTOR-42-PENDENTE"
    assert plan[0]["amount"] == Decimal("200.00")
    assert plan[0]["due_date"] == "2026-07-10"
    assert plan[0]["payment_label"] == "Boleto"
    assert plan[0]["should_settle"] is False


def test_financial_plan_parcial_defaults_to_50_50_and_settles_entry_only():
    mapper = BlingOrderMapper()
    pedido = make_pedido(
        status_pagamento="Parcial",
        pagamento="Pix",
        forma_pagamento_entrada="Pix",
        forma_pagamento_restante="Dinheiro",
    )

    plan = mapper.build_financial_plan(pedido, Decimal("199.90"))

    assert [row["kind"] for row in plan] == ["ENTRADA", "SALDO"]
    assert [row["amount"] for row in plan] == [Decimal("99.95"), Decimal("99.95")]
    assert [row["payment_label"] for row in plan] == ["Pix", "Dinheiro"]
    assert [row["due_date"] for row in plan] == ["2026-06-21", "2026-07-10"]
    assert [row["should_settle"] for row in plan] == [True, False]


def test_financial_plan_parcial_uses_snapshot_amounts():
    mapper = BlingOrderMapper()
    pedido = make_pedido(
        status_pagamento="Parcial",
        pagamento="Pix",
        valor_entrada=Decimal("75.00"),
        valor_restante=Decimal("125.00"),
    )

    plan = mapper.build_financial_plan(pedido, Decimal("200.00"))

    assert [row["amount"] for row in plan] == [Decimal("75.00"), Decimal("125.00")]


def test_financial_plan_rejects_partial_without_payment_forms():
    mapper = BlingOrderMapper()
    pedido = make_pedido(status_pagamento="Parcial", pagamento="")

    with pytest.raises(BlingValidationError, match="entrada/saldo"):
        mapper.build_financial_plan(pedido, Decimal("200.00"))
