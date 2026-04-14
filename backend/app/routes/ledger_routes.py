# -*- coding: utf-8 -*-
"""
Ledger Routes — Extrato, saldo e lançamentos do módulo Recebíveis
"""
import csv
import io
from datetime import date

from flask import Blueprint, request, make_response

from app.decorators.auth_decorator import require_auth
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.common import error_response, success_response
from app.services import ledger_service

ledger_bp = Blueprint("ledger", __name__, url_prefix="/api/ledger")
ledger_repo = LedgerRepository()


def _resolve_user_id() -> tuple:
    """
    Retorna (user_id, error_response).
    - Vendedor: só pode ver o próprio user_id.
    - Admin: pode ver qualquer user_id via ?user_id=X (default: o próprio).
    """
    current = request.current_user
    my_id = current["user_id"]
    role = current["role"]

    if role == "admin":
        try:
            uid = int(request.args.get("user_id") or my_id)
        except (ValueError, TypeError):
            return None, error_response("user_id inválido", 400)
    else:
        uid = my_id

    return uid, None


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _build_live_commission_rows(
    user_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict]:
    """
    Calcula comissões em tempo real para pedidos atribuídos.
    Não altera banco; também informa se já existe ledger entry para evitar dupla soma.
    """
    from sqlalchemy import func

    from app.models.ledger_entry import LedgerEntry
    from app.models.pedido import Pedido
    from app.repositories.user_repository import UserRepository
    from app.services.commission_service import (
        get_monday,
        map_fonte_to_source,
        resolve_commission_reference_date,
    )

    query = Pedido.query.filter(
        Pedido.vendedor_id == user_id,
        Pedido.deleted_at.is_(None),
        func.lower(func.trim(Pedido.status)) != "cancelado",
    )
    if from_date:
        query = query.filter(Pedido.dia_entrega >= from_date)
    if to_date:
        query = query.filter(Pedido.dia_entrega <= to_date)

    pedidos = query.order_by(Pedido.dia_entrega.desc(), Pedido.id.desc()).all()

    user_repo = UserRepository()
    commission_configs = {c.source: c.rate for c in user_repo.get_commission_configs(user_id)}

    existing_entries = (
        LedgerEntry.query.filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type == "CREDIT",
            LedgerEntry.pedido_id.isnot(None),
            LedgerEntry.category.like("comissao_%"),
        )
        .all()
    )
    existing_by_pedido_id = {
        e.pedido_id: e
        for e in existing_entries
        if e.pedido_id is not None
    }

    result = []
    for pedido in pedidos:
        fonte_nome = ""
        if pedido.fonte_pedido_rel:
            fonte_nome = pedido.fonte_pedido_rel.nome or ""
        elif pedido.fonte_pedido:
            fonte_nome = pedido.fonte_pedido or ""

        source = map_fonte_to_source(fonte_nome)
        rate = commission_configs.get(source) if source else None

        valor_pedido = None
        try:
            valor_pedido = pedido.total_pago()
        except Exception:
            valor_pedido = None

        commission_amount = 0.0
        if rate is not None and valor_pedido is not None and valor_pedido > 0:
            commission_amount = round(float(valor_pedido) * float(rate), 2)

        ref_date = resolve_commission_reference_date(pedido)
        week_ref = get_monday(ref_date)
        due_date = ref_date

        status_pagamento = (pedido.status_pagamento or "").strip().lower()
        status = "confirmado" if status_pagamento == "pago" else "pendente"

        existing_entry = existing_by_pedido_id.get(pedido.id)

        result.append({
            "entry_id": existing_entry.id if existing_entry else pedido.id,
            "pedido_id": pedido.id,
            "cliente": pedido.cliente,
            "dia_entrega": pedido.dia_entrega.isoformat() if pedido.dia_entrega else None,
            "week_ref": week_ref.isoformat() if week_ref else None,
            "due_date": due_date.isoformat() if due_date else None,
            "due_date_obj": due_date,
            "valor_pedido": round(float(valor_pedido), 2) if valor_pedido is not None else None,
            "fonte": source,
            "rate": round(rate * 100, 1) if rate is not None else None,
            "commission_amount": commission_amount,
            "status": existing_entry.status if existing_entry else status,
            "has_ledger_entry": existing_entry is not None,
        })

    return result


# ---------------------------------------------------------------------------
# GET /api/ledger/balance
# ---------------------------------------------------------------------------
@ledger_bp.route("/balance", methods=["GET"])
@require_auth(roles=["admin", "vendedor"])
def get_balance():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err

        balance = ledger_service.get_balance(user_id)

        # Complementa saldo com comissões calculadas em tempo real
        # (somente pedidos ainda sem ledger entry de comissão).
        live_rows = _build_live_commission_rows(user_id=user_id)
        today = date.today()
        extra_confirmed = 0.0
        extra_pending = 0.0
        extra_overdue = 0.0

        for row in live_rows:
            if row["has_ledger_entry"] or row["commission_amount"] <= 0:
                continue

            amount = float(row["commission_amount"])
            if row["status"] == "confirmado":
                extra_confirmed += amount
                continue

            due_date = row.get("due_date_obj")
            if due_date and due_date < today:
                extra_overdue += amount
            else:
                extra_pending += amount

        if extra_confirmed or extra_pending or extra_overdue:
            balance["confirmed_credits"] = round(float(balance["confirmed_credits"]) + extra_confirmed, 2)
            balance["pending_credits"] = round(float(balance["pending_credits"]) + extra_pending, 2)
            balance["overdue_credits"] = round(float(balance["overdue_credits"]) + extra_overdue, 2)
            balance["total_credits"] = round(
                float(balance["confirmed_credits"])
                + float(balance["pending_credits"])
                + float(balance["overdue_credits"]),
                2,
            )
            balance["balance"] = round(float(balance["total_credits"]) - float(balance["total_debits"]), 2)

        return success_response({"user_id": user_id, **balance})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/ledger/entries
# ---------------------------------------------------------------------------
@ledger_bp.route("/entries", methods=["GET"])
@require_auth(roles=["admin", "vendedor"])
def get_entries():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err

        week_ref = _parse_date(request.args.get("week_ref"))
        category = request.args.get("category") or None
        from_date = _parse_date(request.args.get("from"))
        to_date = _parse_date(request.args.get("to"))

        entries = ledger_repo.get_entries(
            user_id=user_id,
            week_ref=week_ref,
            category=category,
            from_date=from_date,
            to_date=to_date,
        )
        return success_response(
            {"user_id": user_id, "entries": [e.to_dict() for e in entries]}
        )
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /api/ledger/entries — lançamento manual (admin)
# ---------------------------------------------------------------------------
@ledger_bp.route("/entries", methods=["POST"])
@require_auth(roles=["admin"])
def create_entry():
    try:
        data = request.get_json() or {}
        current = request.current_user

        user_id = data.get("user_id")
        entry_type = (data.get("type") or "").upper()
        category = data.get("category", "")
        amount = data.get("amount")
        description = data.get("description")
        week_ref_str = data.get("week_ref")

        if not all([user_id, entry_type, category, amount]):
            return error_response("user_id, type, category e amount são obrigatórios", 400)

        week_ref = _parse_date(week_ref_str) or date.today()

        entry = ledger_service.create_manual_entry(
            user_id=int(user_id),
            entry_type=entry_type,
            category=category,
            amount=float(amount),
            week_ref=week_ref,
            created_by=current["user_id"],
            description=description,
        )
        return success_response({"entry": entry}, status_code=201)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /api/ledger/generate-weekly — gera créditos fixos da semana (admin)
# ---------------------------------------------------------------------------
@ledger_bp.route("/generate-weekly", methods=["POST"])
@require_auth(roles=["admin"])
def generate_weekly():
    try:
        data = request.get_json() or {}
        current = request.current_user

        week_ref_str = data.get("week_ref")
        week_ref = _parse_date(week_ref_str) or date.today()

        result = ledger_service.generate_weekly_credits(
            week_ref=week_ref,
            created_by=current["user_id"],
        )
        return success_response(result, message="Créditos semanais gerados")
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/ledger/periods — recebíveis agrupados por período (semana)
# ---------------------------------------------------------------------------
@ledger_bp.route("/periods", methods=["GET"])
@require_auth(roles=["admin", "vendedor"])
def get_periods():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err
        result = ledger_service.get_period_summary(user_id)
        return success_response(result)
    except Exception as e:
        return error_response(str(e), 500)


# GET /api/ledger/pedidos — pedidos atribuídos com detalhes de comissão
# ---------------------------------------------------------------------------
@ledger_bp.route("/pedidos", methods=["GET"])
@require_auth(roles=["admin", "vendedor"])
def get_pedidos_atribuidos():
    """
    Retorna pedidos com comissão gerada para o vendedor.
    Cada item contém: pedido_id, cliente, dia_entrega, due_date,
    valor_pedido, fonte, rate (%), commission_amount.
    Filtros opcionais: ?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err

        from_date = _parse_date(request.args.get("from", ""))
        to_date = _parse_date(request.args.get("to", ""))
        rows = _build_live_commission_rows(user_id=user_id, from_date=from_date, to_date=to_date)
        result = [
            {k: v for k, v in row.items() if k not in ("has_ledger_entry", "due_date_obj")}
            for row in rows
        ]
        return success_response({"pedidos": result, "total": len(result)})

    except Exception as e:
        return error_response(str(e), 500)


# GET /api/ledger/summary — saldo de todos os vendedores (admin)
# ---------------------------------------------------------------------------
@ledger_bp.route("/summary", methods=["GET"])
@require_auth(roles=["admin"])
def get_summary():
    try:
        balances = ledger_repo.get_all_balances()
        return success_response({"summary": balances})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/ledger/pending — pagamentos pendentes de confirmação
# ---------------------------------------------------------------------------
@ledger_bp.route("/pending", methods=["GET"])
@require_auth(roles=["admin", "vendedor"])
def get_pending():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err

        entries = ledger_repo.get_pending(user_id)
        return success_response(
            {"user_id": user_id, "entries": [e.to_dict() for e in entries]}
        )
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# PUT /api/ledger/entries/<id>/confirm — funcionário confirma recebimento
# ---------------------------------------------------------------------------
@ledger_bp.route("/entries/<int:entry_id>/confirm", methods=["PUT"])
@require_auth(roles=["admin", "vendedor"])
def confirm_entry(entry_id: int):
    try:
        current = request.current_user
        is_admin = current["role"] == "admin"
        entry = ledger_repo.confirm_entry(
            entry_id=entry_id,
            user_id=current["user_id"],
            is_admin=is_admin,
        )
        if entry is None:
            return error_response("Lançamento não encontrado ou sem permissão", 404)
        return success_response({"entry": entry.to_dict()})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /api/ledger/generate-calendar — gera calendário de créditos (admin)
# ---------------------------------------------------------------------------
@ledger_bp.route("/generate-calendar", methods=["POST"])
@require_auth(roles=["admin"])
def generate_calendar():
    try:
        data = request.get_json() or {}
        current = request.current_user

        n_weeks = int(data.get("n_weeks") or 4)
        from_week_str = data.get("from_week")
        from_week = _parse_date(from_week_str) or date.today()

        result = ledger_service.generate_calendar(
            n_weeks=n_weeks,
            created_by=current["user_id"],
            from_week=from_week,
        )
        return success_response(result, message=f"Calendário de {n_weeks} semanas gerado")
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/ledger/export — exporta extrato em CSV
# ---------------------------------------------------------------------------
@ledger_bp.route("/export", methods=["GET"])
@require_auth(roles=["admin", "vendedor"])
def export_csv():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err

        from_date = _parse_date(request.args.get("from"))
        to_date = _parse_date(request.args.get("to"))

        entries = ledger_repo.get_entries(user_id=user_id, from_date=from_date, to_date=to_date)

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "week_ref", "type", "category", "amount", "description", "pedido_id", "created_at"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for e in entries:
            writer.writerow(e.to_dict())

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename=extrato_{user_id}.csv"
        return response
    except Exception as e:
        return error_response(str(e), 500)
