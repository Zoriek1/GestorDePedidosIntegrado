# -*- coding: utf-8 -*-
"""
Ledger Routes — Extrato, saldo e quitação do módulo Recebíveis (double-entry)
"""
import csv
import io
from datetime import date

from flask import Blueprint, make_response, request

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


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# GET /api/ledger/balance
# ---------------------------------------------------------------------------
@ledger_bp.route("/balance", methods=["GET"])
@require_auth(roles=["admin", "vendedor", "entregador"])
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
# POST /api/ledger/settle — quitação em lote (substitui confirm individual)
# ---------------------------------------------------------------------------
@ledger_bp.route("/settle", methods=["POST"])
@require_auth(roles=["admin", "vendedor", "entregador"])
def settle():
    """
    Quita CREDITs ativos selecionados por entry_ids e/ou pedido_ids em uma transação atômica.
    Admin pode quitar qualquer vendedor via body {"user_id": X}.
    Vendedor quita apenas a si mesmo.
    Sem "marcar todos": precisa de lista explícita.
    """
    try:
        current = request.current_user
        my_id = current["user_id"]
        role = current["role"]

        data = request.get_json() or {}

        if role == "admin":
            try:
                user_id = int(data.get("user_id") or my_id)
            except (ValueError, TypeError):
                return error_response("user_id inválido", 400)
        else:
            user_id = my_id

        def _normalize_ids(field_name: str) -> tuple[list[int] | None, tuple | None]:
            raw_ids = data.get(field_name)
            if raw_ids is None:
                return None, None
            if not isinstance(raw_ids, list):
                return None, error_response(f"{field_name} deve ser um array", 400)

            normalized: list[int] = []
            seen = set()
            for raw in raw_ids:
                try:
                    item_id = int(raw)
                except (ValueError, TypeError):
                    return None, error_response(
                        f"{field_name} deve conter apenas inteiros válidos",
                        400,
                    )
                if item_id <= 0:
                    return None, error_response(
                        f"{field_name} deve conter apenas inteiros positivos",
                        400,
                    )
                if item_id in seen:
                    return None, error_response(f"{field_name} deve conter IDs únicos", 400)
                seen.add(item_id)
                normalized.append(item_id)
            return normalized, None

        pedido_ids, err_pedido = _normalize_ids("pedido_ids")
        if err_pedido:
            return err_pedido
        entry_ids, err_entry = _normalize_ids("entry_ids")
        if err_entry:
            return err_entry

        pedido_ids = pedido_ids or []
        entry_ids = entry_ids or []
        if len(pedido_ids) == 0 and len(entry_ids) == 0:
            return error_response("entry_ids ou pedido_ids é obrigatório", 400)

        result = ledger_service.settle_user_credits(
            user_id=user_id,
            settled_by=my_id,
            pedido_ids=pedido_ids,
            entry_ids=entry_ids,
        )

        return success_response(result, message=f"{result['settled']} crédito(s) quitado(s)")
    except Exception as e:
        return error_response(str(e), 500)

# ---------------------------------------------------------------------------
# GET /api/ledger/entries
# ---------------------------------------------------------------------------
@ledger_bp.route("/entries", methods=["GET"])
@require_auth(roles=["admin", "vendedor", "entregador"])
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
        return success_response({"user_id": user_id, "entries": [e.to_dict() for e in entries]})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# DELETE /api/ledger/entries/<id> — apaga lançamento de salário (admin)
# ---------------------------------------------------------------------------
@ledger_bp.route("/entries/<int:entry_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_salary_entry(entry_id):
    """
    Soft-delete (voided=true) de salário fixo_semanal/almoco/transporte.
    Bloqueado para comissões e para entradas já liquidadas.
    """
    try:
        current = request.current_user
        result = ledger_service.void_salary_entry(entry_id=entry_id, actor_id=current["user_id"])
        return success_response({"entry": result}, message="Lançamento apagado")
    except LookupError as e:
        return error_response(str(e), 404)
    except PermissionError as e:
        return error_response(str(e), 403)
    except ValueError as e:
        return error_response(str(e), 409)
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
# GET /api/ledger/periods — recebíveis agrupados por período (due_date)
# ---------------------------------------------------------------------------
@ledger_bp.route("/periods", methods=["GET"])
@require_auth(roles=["admin", "vendedor", "entregador"])
def get_periods():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err
        result = ledger_service.get_period_summary(user_id)
        return success_response(result)
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/ledger/pedidos — pedidos atribuídos com detalhes de comissão (admin)
# ---------------------------------------------------------------------------
@ledger_bp.route("/pedidos", methods=["GET"])
@require_auth(roles=["admin", "vendedor", "entregador"])
def get_pedidos_atribuidos():
    """
    Retorna pedidos com CREDIT gerado para o usuário (view administrativa):
      - Comissões do vendedor (via pedido_id, categoria comissao_*).
      - Taxas de entrega do entregador (via delivery_pedido_id, categoria taxa_entrega).
    Lê diretamente dos ledger entries sem recalcular em tempo real.
    """
    try:
        from sqlalchemy import or_

        user_id, err = _resolve_user_id()
        if err:
            return err

        from_date = _parse_date(request.args.get("from", ""))
        to_date = _parse_date(request.args.get("to", ""))

        from app.models.ledger_entry import LedgerEntry
        from app.models.pedido import Pedido
        from app.repositories.user_repository import UserRepository
        from app.services.commission_service import map_fonte_to_source

        query = LedgerEntry.query.filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type == "CREDIT",
            LedgerEntry.voided.is_(False),
            or_(
                # Comissão do vendedor: pedido_id preenchido + categoria comissao_*
                (LedgerEntry.pedido_id.isnot(None))
                & (LedgerEntry.category.like("comissao_%")),
                # Taxa de entrega do entregador: delivery_pedido_id preenchido + categoria taxa_entrega
                (LedgerEntry.delivery_pedido_id.isnot(None))
                & (LedgerEntry.category == "taxa_entrega"),
            ),
        )

        entries = query.order_by(LedgerEntry.week_ref.desc(), LedgerEntry.created_at.desc()).all()

        # Coleta ids dos pedidos (de qualquer dos dois campos)
        pedido_ids: list[int] = []
        for e in entries:
            pid = e.pedido_id or e.delivery_pedido_id
            if pid:
                pedido_ids.append(pid)

        pedidos_by_id = (
            {p.id: p for p in Pedido.query.filter(Pedido.id.in_(pedido_ids)).all()}
            if pedido_ids
            else {}
        )
        user_repo = UserRepository()

        result = []
        for entry in entries:
            pid = entry.pedido_id or entry.delivery_pedido_id
            pedido = pedidos_by_id.get(pid) if pid else None
            if from_date and pedido and pedido.dia_entrega and pedido.dia_entrega < from_date:
                continue
            if to_date and pedido and pedido.dia_entrega and pedido.dia_entrega > to_date:
                continue

            fonte_nome = None
            fonte_pedido_id = None
            valor_pedido = None
            rate = None
            is_delivery = entry.category == "taxa_entrega"

            if pedido:
                fonte_pedido_id = pedido.fonte_pedido_id
                if pedido.fonte_pedido_rel:
                    fonte_nome = pedido.fonte_pedido_rel.nome
                else:
                    fonte_nome = pedido.fonte_pedido
                try:
                    valor_pedido = float(pedido.total_pago())
                except Exception:
                    valor_pedido = None
                if not is_delivery:
                    cfg = user_repo.get_active_commission(
                        user_id=user_id,
                        fonte_pedido_id=fonte_pedido_id,
                        source=map_fonte_to_source(fonte_nome or ""),
                    )
                    if cfg:
                        rate = round(float(cfg.rate) * 100, 2)

            # Para CREDIT de taxa_entrega, sobrescrever o rótulo de "fonte"
            # com "Taxa de entrega" para a UI ficar clara.
            display_fonte = "Taxa de entrega" if is_delivery else fonte_nome

            result.append(
                {
                    "entry_id": entry.id,
                    "pedido_id": pid,
                    "cliente": pedido.cliente if pedido else None,
                    "dia_entrega": pedido.dia_entrega.isoformat()
                    if pedido and pedido.dia_entrega
                    else None,
                    "week_ref": entry.week_ref.isoformat() if entry.week_ref else None,
                    "due_date": entry.due_date.isoformat() if entry.due_date else None,
                    "commission_amount": float(entry.amount),
                    "category": entry.category,
                    "fonte_pedido_id": fonte_pedido_id,
                    "fonte": display_fonte,
                    "rate": rate,
                    "valor_pedido": valor_pedido,
                    "status": entry.status,
                    "settled_at": entry.settled_at.strftime("%Y-%m-%d %H:%M:%S")
                    if entry.settled_at
                    else None,
                    "settled_by_id": entry.settled_by_id,
                }
            )

        return success_response({"pedidos": result, "total": len(result)})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/ledger/commissions — comissões agregadas POR VENDEDOR num período
# Pensado para consumo externo (BI / dashboard próprio). Só comissões (comissao_*).
# ---------------------------------------------------------------------------
@ledger_bp.route("/commissions", methods=["GET"])
@require_auth(roles=["admin"])
def get_commissions():
    """
    Retorna comissões agregadas por vendedor num período, em JSON.

    Query params:
      from, to      YYYY-MM-DD (inclusive) — intervalo do período. Opcionais.
      date_basis    entrega (default) | vencimento | competencia
                      - entrega:    filtra por pedido.dia_entrega
                      - vencimento: filtra por ledger_entry.due_date
                      - competencia: filtra por ledger_entry.week_ref (segunda da semana)
      user_id       int — restringe a um único vendedor (opcional).
      detail        true|false (default false) — inclui a lista de pedidos por vendedor.
    """
    try:
        from app.models.ledger_entry import LedgerEntry
        from app.models.pedido import Pedido
        from app.models.user import User

        from_date = _parse_date(request.args.get("from"))
        to_date = _parse_date(request.args.get("to"))
        date_basis = (request.args.get("date_basis") or "entrega").strip().lower()
        if date_basis not in {"entrega", "vencimento", "competencia"}:
            return error_response(
                "date_basis deve ser entrega, vencimento ou competencia", 400
            )
        want_detail = _parse_bool(request.args.get("detail"), default=False)

        filter_user_id = None
        if request.args.get("user_id"):
            try:
                filter_user_id = int(request.args.get("user_id"))
            except (ValueError, TypeError):
                return error_response("user_id inválido", 400)

        q = LedgerEntry.query.filter(
            LedgerEntry.type == "CREDIT",
            LedgerEntry.voided.is_(False),
            LedgerEntry.category.like("comissao_%"),
        )
        if filter_user_id is not None:
            q = q.filter(LedgerEntry.user_id == filter_user_id)

        # Filtro por data direto na entry (vencimento/competência)
        if date_basis == "vencimento":
            if from_date:
                q = q.filter(LedgerEntry.due_date.isnot(None), LedgerEntry.due_date >= from_date)
            if to_date:
                q = q.filter(LedgerEntry.due_date.isnot(None), LedgerEntry.due_date <= to_date)
        elif date_basis == "competencia":
            if from_date:
                q = q.filter(LedgerEntry.week_ref >= from_date)
            if to_date:
                q = q.filter(LedgerEntry.week_ref <= to_date)

        entries = q.all()

        pedido_ids = [e.pedido_id for e in entries if e.pedido_id]
        pedidos_by_id = (
            {p.id: p for p in Pedido.query.filter(Pedido.id.in_(pedido_ids)).all()}
            if pedido_ids
            else {}
        )
        user_ids = {e.user_id for e in entries}
        users_by_id = (
            {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
            if user_ids
            else {}
        )

        agg: dict[int, dict] = {}
        for e in entries:
            pedido = pedidos_by_id.get(e.pedido_id) if e.pedido_id else None

            # Filtro por data de entrega (basis=entrega): exige o pedido no intervalo.
            if date_basis == "entrega":
                de = pedido.dia_entrega if pedido else None
                if from_date and (de is None or de < from_date):
                    continue
                if to_date and (de is None or de > to_date):
                    continue

            user = users_by_id.get(e.user_id)
            bucket = agg.setdefault(
                e.user_id,
                {
                    "user_id": e.user_id,
                    "name": user.name if user else None,
                    "email": user.email if user else None,
                    "total_commission": 0.0,
                    "paid_commission": 0.0,
                    "pending_commission": 0.0,
                    "orders_count": 0,
                    "_by_source": {},
                    "items": [],
                },
            )

            amt = float(e.amount)
            bucket["total_commission"] += amt
            if e.status == "settled":
                bucket["paid_commission"] += amt
            else:
                bucket["pending_commission"] += amt
            bucket["orders_count"] += 1

            source = e.commission_source or (
                e.category[len("comissao_"):]
                if e.category.startswith("comissao_")
                else e.category
            )
            src = bucket["_by_source"].setdefault(
                source, {"source": source, "total": 0.0, "orders_count": 0}
            )
            src["total"] += amt
            src["orders_count"] += 1

            if want_detail:
                bucket["items"].append(
                    {
                        "entry_id": e.id,
                        "pedido_id": e.pedido_id,
                        "cliente": pedido.cliente if pedido else None,
                        "dia_entrega": pedido.dia_entrega.isoformat()
                        if pedido and pedido.dia_entrega
                        else None,
                        "week_ref": e.week_ref.isoformat() if e.week_ref else None,
                        "due_date": e.due_date.isoformat() if e.due_date else None,
                        "commission_amount": round(amt, 2),
                        "commission_rate_pct": round(float(e.commission_rate) * 100, 2)
                        if e.commission_rate is not None
                        else None,
                        "source": source,
                        "category": e.category,
                        "status": e.status,
                        "settled_at": e.settled_at.strftime("%Y-%m-%d %H:%M:%S")
                        if e.settled_at
                        else None,
                    }
                )

        vendedores = []
        for b in agg.values():
            b["total_commission"] = round(b["total_commission"], 2)
            b["paid_commission"] = round(b["paid_commission"], 2)
            b["pending_commission"] = round(b["pending_commission"], 2)
            by_source = sorted(
                b.pop("_by_source").values(), key=lambda s: s["total"], reverse=True
            )
            for s in by_source:
                s["total"] = round(s["total"], 2)
            b["by_source"] = by_source
            if not want_detail:
                b.pop("items", None)
            vendedores.append(b)
        vendedores.sort(key=lambda v: v["total_commission"], reverse=True)

        totals = {
            "total_commission": round(sum(v["total_commission"] for v in vendedores), 2),
            "paid_commission": round(sum(v["paid_commission"] for v in vendedores), 2),
            "pending_commission": round(sum(v["pending_commission"] for v in vendedores), 2),
            "orders_count": sum(v["orders_count"] for v in vendedores),
            "vendedores_count": len(vendedores),
        }

        return success_response(
            {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
                "date_basis": date_basis,
                "totals": totals,
                "vendedores": vendedores,
            }
        )
    except Exception:
        return error_response("Erro ao gerar relatório de comissões", 500)


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
# GET /api/ledger/pending — CREDITs active do vendedor
# ---------------------------------------------------------------------------
@ledger_bp.route("/pending", methods=["GET"])
@require_auth(roles=["admin", "vendedor", "entregador"])
def get_pending():
    try:
        user_id, err = _resolve_user_id()
        if err:
            return err

        competencia_tipo = (request.args.get("competencia_tipo") or "semanal").strip().lower()
        if competencia_tipo not in {"semanal", "mensal"}:
            return error_response("competencia_tipo deve ser 'semanal' ou 'mensal'", 400)
        competencia = (request.args.get("competencia") or "").strip() or None
        include_quitados = _parse_bool(request.args.get("include_quitados"), default=False)

        payload = ledger_repo.get_pending_sections(
            user_id=user_id,
            competencia_tipo=competencia_tipo,
            competencia=competencia,
            include_quitados=include_quitados,
        )
        return success_response({"user_id": user_id, **payload})
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
@require_auth(roles=["admin", "vendedor", "entregador"])
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
            fieldnames=[
                "id",
                "week_ref",
                "type",
                "category",
                "amount",
                "description",
                "pedido_id",
                "status",
                "settled_at",
                "created_at",
            ],
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
