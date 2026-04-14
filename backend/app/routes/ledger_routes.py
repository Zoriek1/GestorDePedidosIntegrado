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
