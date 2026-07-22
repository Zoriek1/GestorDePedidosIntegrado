# -*- coding: utf-8 -*-
"""Mapper Pedido interno -> payload Bling."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List

from flask import current_app

from app.integrations.bling.errors import BlingValidationError
from app.models.bling_payment_mapping import BlingPaymentMapping

CENT = Decimal("0.01")


def parse_decimal_money(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)

    text = str(value).strip().replace("R$", "").strip()
    if not text:
        return Decimal("0.00")
    text = "".join(ch for ch in text if ch.isdigit() or ch in ",.-")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return Decimal(text).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def money_float(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _date_str(value) -> str | None:
    if not value:
        return None
    if hasattr(value, "date") and not hasattr(value, "isoformat"):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
        return value.date().isoformat() if hasattr(value, "hour") else value.isoformat()
    return str(value)[:10]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _external_marker(pedido_id: int, kind: str) -> str:
    return f"GESTOR-{pedido_id}-{kind}"


def _payment_status(pedido) -> str:
    status = _clean(getattr(pedido, "status_pagamento", None)) or "Pendente"
    if status.lower().startswith("parcial"):
        return "Parcial"
    if status.lower() in {"pago", "realizado"}:
        return "Pago"
    return "Pendente"


def _bling_id(value: str) -> int | str:
    raw = str(value)
    return int(raw) if raw.isdigit() else raw


class BlingOrderMapper:
    def build(self, pedido) -> Dict[str, Any]:
        total = parse_decimal_money(getattr(pedido, "valor", None))
        if total <= Decimal("0.00"):
            raise BlingValidationError("Pedido sem valor valido para envio ao Bling")

        plan = self.build_financial_plan(pedido, total)
        mappings = self.resolve_mappings(plan)
        payload = self.build_payload(pedido, total, plan, mappings)
        return {
            "payload": payload,
            "financial_plan": plan,
            "mappings": mappings,
        }

    def build_financial_plan(self, pedido, total: Decimal) -> List[Dict[str, Any]]:
        status = _payment_status(pedido)
        created_date = _date_str(
            getattr(pedido, "paid_at", None) or getattr(pedido, "created_at", None)
        )
        delivery_date = _date_str(getattr(pedido, "dia_entrega", None))
        main_payment = _clean(getattr(pedido, "pagamento", None))

        if not delivery_date:
            raise BlingValidationError("Pedido sem dia_entrega para vencimento financeiro")

        if status == "Pago":
            if not main_payment:
                raise BlingValidationError("Pedido pago sem forma de pagamento")
            return [
                {
                    "kind": "PAGO",
                    "marker": _external_marker(pedido.id, "PAGO"),
                    "amount": total,
                    "due_date": created_date or delivery_date,
                    "payment_label": main_payment,
                    "should_settle": True,
                }
            ]

        if status == "Parcial":
            entry = parse_decimal_money(getattr(pedido, "valor_entrada", None))
            if entry <= Decimal("0.00"):
                entry = (total * Decimal("0.50")).quantize(CENT, rounding=ROUND_HALF_UP)
            balance = parse_decimal_money(getattr(pedido, "valor_restante", None))
            if balance <= Decimal("0.00"):
                balance = (total - entry).quantize(CENT, rounding=ROUND_HALF_UP)
            if entry <= Decimal("0.00") or balance <= Decimal("0.00"):
                raise BlingValidationError("Pedido parcial precisa ter entrada e saldo positivos")

            entry_payment = _clean(getattr(pedido, "forma_pagamento_entrada", None)) or main_payment
            balance_payment = (
                _clean(getattr(pedido, "forma_pagamento_restante", None)) or main_payment
            )
            if not entry_payment or not balance_payment:
                raise BlingValidationError("Pedido parcial sem forma de pagamento da entrada/saldo")

            return [
                {
                    "kind": "ENTRADA",
                    "marker": _external_marker(pedido.id, "ENTRADA"),
                    "amount": entry,
                    "due_date": created_date or delivery_date,
                    "payment_label": entry_payment,
                    "should_settle": True,
                },
                {
                    "kind": "SALDO",
                    "marker": _external_marker(pedido.id, "SALDO"),
                    "amount": balance,
                    "due_date": delivery_date,
                    "payment_label": balance_payment,
                    "should_settle": False,
                },
            ]

        if not main_payment:
            raise BlingValidationError("Pedido pendente sem forma de pagamento prevista")
        return [
            {
                "kind": "PENDENTE",
                "marker": _external_marker(pedido.id, "PENDENTE"),
                "amount": total,
                "due_date": delivery_date,
                "payment_label": main_payment,
                "should_settle": False,
            }
        ]

    def resolve_mappings(self, plan: List[Dict[str, Any]]) -> Dict[str, BlingPaymentMapping]:
        labels = sorted({row["payment_label"] for row in plan if row.get("payment_label")})
        mappings = {
            mapping.gestor_payment_label: mapping
            for mapping in BlingPaymentMapping.query.filter(
                BlingPaymentMapping.gestor_payment_label.in_(labels),
                BlingPaymentMapping.active.is_(True),
            ).all()
        }
        missing = [label for label in labels if label not in mappings]
        if missing:
            raise BlingValidationError(
                "Forma de pagamento sem mapeamento Bling",
                details={"missing_payment_labels": missing},
            )

        incomplete = []
        for row in plan:
            mapping = mappings[row["payment_label"]]
            if not mapping.payment_method:
                incomplete.append(f"{row['payment_label']}: forma Bling")
            if row.get("should_settle") and not mapping.financial_account:
                incomplete.append(f"{row['payment_label']}: portador/conta")
            if row.get("should_settle") and not mapping.category:
                incomplete.append(f"{row['payment_label']}: categoria")
        if incomplete:
            raise BlingValidationError(
                "Mapeamento Bling incompleto",
                details={"missing_mapping_parts": incomplete},
            )
        return mappings

    def build_payload(
        self,
        pedido,
        total: Decimal,
        plan: List[Dict[str, Any]],
        mappings: Dict[str, BlingPaymentMapping],
    ) -> Dict[str, Any]:
        data_pedido = _date_str(getattr(pedido, "created_at", None)) or _date_str(
            getattr(pedido, "dia_entrega", None)
        )
        entrega = _date_str(getattr(pedido, "dia_entrega", None)) or data_pedido
        descricao = " | ".join(
            part
            for part in [
                _clean(getattr(pedido, "produto", None)),
                _clean(getattr(pedido, "flores_cor", None)),
            ]
            if part
        )
        if not descricao:
            descricao = "Pedido floricultura"

        parcelas = []
        for row in plan:
            mapping = mappings[row["payment_label"]]
            parcelas.append(
                {
                    "dataVencimento": row["due_date"],
                    "valor": money_float(row["amount"]),
                    "observacoes": f"{row['marker']} - {row['kind']}",
                    "formaPagamento": {"id": _bling_id(mapping.payment_method.bling_id)},
                }
            )

        contato: Dict[str, Any] = {
            "nome": _clean(getattr(pedido, "cliente", None)) or "Cliente Gestor",
            "telefone": _clean(getattr(pedido, "telefone_cliente", None)),
        }
        # O Bling exige contato.id na venda. Se um id fixo estiver configurado,
        # ja vai no payload (e reflete no preview); senao o service resolve/cria
        # o contato generico antes de criar a venda.
        default_contact = _clean(current_app.config.get("BLING_DEFAULT_CONTACT_ID"))
        if default_contact:
            contato["id"] = _bling_id(default_contact)

        payload: Dict[str, Any] = {
            "numeroLoja": f"GESTOR-{pedido.id}",
            "data": data_pedido,
            "dataSaida": entrega,
            "dataPrevista": entrega,
            "contato": contato,
            "itens": [
                {
                    "codigo": current_app.config.get("BLING_DEFAULT_PRODUCT_CODE")
                    or "PEDIDO-FLORICULTURA",
                    "unidade": "UN",
                    "quantidade": 1,
                    "valor": money_float(total),
                    "descricao": descricao,
                }
            ],
            "parcelas": parcelas,
            "observacoesInternas": self._observacoes_internas(pedido),
        }

        etiqueta = self._etiqueta_entrega(pedido)
        if etiqueta:
            payload["transporte"] = {"etiqueta": etiqueta}

        return payload

    def _etiqueta_entrega(self, pedido) -> Dict[str, Any] | None:
        if (_clean(getattr(pedido, "tipo_pedido", None)).lower() or "entrega") == "retirada":
            return None
        return {
            "nome": _clean(getattr(pedido, "destinatario", None))
            or _clean(getattr(pedido, "cliente", None)),
            "endereco": _clean(getattr(pedido, "rua", None))
            or _clean(getattr(pedido, "endereco", None)),
            "numero": _clean(getattr(pedido, "numero", None)),
            "complemento": _clean(getattr(pedido, "complemento", None))
            or _clean(getattr(pedido, "apto", None)),
            "municipio": _clean(getattr(pedido, "cidade", None)),
            "uf": (
                _clean(getattr(pedido, "uf", None)) or _clean(getattr(pedido, "estado", None))
            ).upper(),
            "cep": _clean(getattr(pedido, "cep", None)),
            "bairro": _clean(getattr(pedido, "bairro", None)),
            "nomePais": "Brasil",
        }

    def _observacoes_internas(self, pedido) -> str:
        lines = [
            f"Pedido Gestor: #{pedido.id}",
            f"Cliente/remetente: {_clean(getattr(pedido, 'cliente', None))}",
            f"Telefone: {_clean(getattr(pedido, 'telefone_cliente', None))}",
            f"Destinatario: {_clean(getattr(pedido, 'destinatario', None))}",
            f"Entrega: {_date_str(getattr(pedido, 'dia_entrega', None)) or ''} {_clean(getattr(pedido, 'horario', None))}",
            f"Endereco: {_clean(getattr(pedido, 'endereco', None))}",
        ]
        if _clean(getattr(pedido, "mensagem", None)):
            lines.append(f"Mensagem do cartao: {_clean(getattr(pedido, 'mensagem', None))}")
        if _clean(getattr(pedido, "obs_entrega", None)):
            lines.append(f"Observacoes de entrega: {_clean(getattr(pedido, 'obs_entrega', None))}")
        if _clean(getattr(pedido, "observacoes", None)):
            lines.append(f"Observacoes internas: {_clean(getattr(pedido, 'observacoes', None))}")
        return "\n".join(line for line in lines if line.strip())
