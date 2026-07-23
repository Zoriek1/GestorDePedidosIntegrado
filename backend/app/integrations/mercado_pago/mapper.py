# -*- coding: utf-8 -*-
"""Mapper pagamento MP -> payload Bling (conta a receber)."""

from decimal import Decimal, InvalidOperation


CENT = Decimal("0.01")

CONTACT_NAME = "Mercado Pago [Maquininha]"
CATEGORY_NAME = "Vendas"
FINANCIAL_ACCOUNT_NAME = "Mercado Pago Point"
PAYMENT_LABEL = "Mercado Pago Point"


def parse_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(CENT)
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(CENT)
    text = str(value).strip().replace("R$", "").strip()
    if not text:
        return Decimal("0.00")
    text = "".join(ch for ch in text if ch.isdigit() or ch in ",.-")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return Decimal(text).quantize(CENT)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


class MercadoPagoReceivableMapper:
    def extract_payment_info(self, payment: dict) -> dict:
        payment_id = str(payment.get("id", ""))
        amount = parse_decimal(payment.get("transaction_amount"))
        net_amount = parse_decimal(
            payment.get("transaction_details", {}).get("net_received_amount")
        )
        # fallback: se net_amount for zero ou ausente, usa amount
        if net_amount <= Decimal("0.00"):
            net_amount = amount

        return {
            "mp_payment_id": payment_id,
            "amount": amount,
            "net_amount": net_amount,
            "payment_method_id": str(payment.get("payment_method_id", "")),
            "payment_type_id": str(payment.get("payment_type_id", "")),
            "status": str(payment.get("status", "")),
            "date_approved": str(payment.get("date_approved", "")),
            "description": f"Venda Point #{payment_id}",
        }

    def should_process(self, payment: dict) -> tuple:
        status = str(payment.get("status", ""))
        if status != "approved":
            return False, f"Status '{status}', ignorando"
        payment_type = str(payment.get("payment_type_id", ""))
        if payment_type != "point_of_sale":
            return False, f"Tipo '{payment_type}', ignorando"
        return True, ""

    def build_bling_receivable_payload(
        self,
        info: dict,
        contact_id: str,
        category_id: str,
        financial_account_id: str,
    ) -> dict:
        due_date = info["date_approved"][:10] if info["date_approved"] else None
        return {
            "contato": {"id": contact_id},
            "valor": float(info["net_amount"]),
            "vencimento": due_date,
            "situacao": {"valor": 1},  # 1 = aberta
            "observacao": info["description"],
            "categoria": {"id": category_id},
            "contaFinanceira": {"id": financial_account_id},
        }

    def build_bling_settle_payload(
        self,
        info: dict,
        financial_account_id: str,
        category_id: str,
    ) -> dict:
        return {
            "data": info["date_approved"][:10] if info["date_approved"] else None,
            "usarDataVencimento": False,
            "portador": {"id": financial_account_id},
            "categoria": {"id": category_id},
            "historico": f"{info['description']} - baixa Gestor",
            "valorRecebido": float(info["net_amount"]),
        }
