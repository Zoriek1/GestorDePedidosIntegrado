# -*- coding: utf-8 -*-
"""
User Routes — CRUD de usuários e configuração de remuneração/comissão (admin only)
"""
from flask import Blueprint, g, request

from app.decorators.auth_decorator import require_auth
from app.repositories.user_repository import UserRepository
from app.schemas.common import error_response, success_response

users_bp = Blueprint("users", __name__, url_prefix="/api/users")
user_repo = UserRepository()


def _current_store_id():
    """ID da loja autenticada da request, ou None (caminho legado sem tenant)."""
    store = getattr(g, "current_store", None)
    return store.id if store is not None else None


def _in_current_store(user) -> bool:
    """Escopo multi-tenant para operações administrativas de usuário.

    Durante o rollout um usuário está no escopo quando não há loja no contexto
    (suítes legadas), quando o alvo ainda não tem loja (nulo, legado) ou quando a
    loja do alvo bate com a loja autenticada. Um admin nunca gerencia usuários de
    outra loja com store_ref_id explícito e diferente.
    """
    store_id = _current_store_id()
    if store_id is None:
        return True
    return user.store_ref_id is None or user.store_ref_id == store_id


# ---------------------------------------------------------------------------
# GET /api/users — lista todos os usuários
# ---------------------------------------------------------------------------
@users_bp.route("", methods=["GET"])
@require_auth(roles=["admin"])
def list_users():
    """Lista usuários. Use ?include_inactive=true para incluir desativados."""
    try:
        include_inactive = request.args.get("include_inactive", "").lower() == "true"
        if include_inactive:
            users = user_repo.get_all()
        else:
            users = user_repo.get_all_active()
        # Esconde tombstones (já apagados): email começa com "deleted_"
        users = [u for u in users if not (u.email or "").startswith("deleted_")]
        # Escopo por loja (multi-tenant): admin só enxerga a própria loja.
        users = [u for u in users if _in_current_store(u)]
        return success_response({"users": [u.to_dict() for u in users]})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/users/entregadores — listagem leve (id, name) de entregadores ativos
# Disponível para admin, vendedor e atendente (precisam atribuir entregas).
# ---------------------------------------------------------------------------
@users_bp.route("/entregadores", methods=["GET"])
@require_auth(roles=["admin", "vendedor", "atendente"])
def list_entregadores():
    try:
        users = user_repo.get_active_by_role("entregador")
        users = [u for u in users if _in_current_store(u)]
        return success_response(
            {"users": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}
        )
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /api/users — cria usuário
# ---------------------------------------------------------------------------
@users_bp.route("", methods=["POST"])
@require_auth(roles=["admin"])
def create_user():
    try:
        from app.services.auth_service import hash_password

        data = request.get_json() or {}
        email = (data.get("email") or "").strip()
        name = (data.get("name") or "").strip()
        password = (data.get("password") or "").strip()
        role = data.get("role", "vendedor")

        if not email or not name or not password:
            return error_response("email, name e password são obrigatórios", 400)
        if len(password) < 8:
            return error_response("Senha deve ter pelo menos 8 caracteres", 400)
        if role not in ("admin", "vendedor", "atendente", "entregador", "viewer"):
            return error_response(
                "role deve ser admin, vendedor, atendente, entregador ou viewer", 400
            )

        if user_repo.get_by_email(email):
            return error_response(f"Email '{email}' já cadastrado", 409)
        if user_repo.get_active_by_name(name):
            return error_response(
                f"Nome '{name}' já está em uso por outro usuário. Escolha outro.", 409
            )

        # A loja vem SEMPRE da identidade autenticada — um store_ref_id enviado no
        # payload é ignorado com segurança (não é aceito de usuário comum).
        user = user_repo.create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            store_ref_id=_current_store_id(),
        )
        return success_response({"user": user.to_dict()}, status_code=201)
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# PUT /api/users/<id> — edita usuário
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>", methods=["PUT"])
@require_auth(roles=["admin"])
def update_user(user_id):
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)

        data = request.get_json() or {}
        updates = {}

        if "name" in data:
            new_name = data["name"].strip()
            if not new_name:
                return error_response("Nome não pode ser vazio", 400)
            conflict = [u for u in user_repo.get_active_by_name(new_name) if u.id != user_id]
            if conflict:
                return error_response(
                    f"Nome '{new_name}' já está em uso por outro usuário. Escolha outro.", 409
                )
            updates["name"] = new_name
        if "role" in data:
            if data["role"] not in ("admin", "vendedor", "atendente", "entregador", "viewer"):
                return error_response(
                    "role deve ser admin, vendedor, atendente, entregador ou viewer", 400
                )
            # Admin não pode se auto-rebaixar (perderia acesso ao painel)
            current = request.current_user
            if (
                current["user_id"] == user_id
                and current.get("role") == "admin"
                and data["role"] != "admin"
            ):
                return error_response(
                    "Admin não pode alterar o próprio cargo. Peça a outro admin.",
                    400,
                )
            updates["role"] = data["role"]
        if "is_active" in data:
            updates["is_active"] = bool(data["is_active"])
        if "password" in data:
            pw = data["password"].strip()
            if len(pw) < 8:
                return error_response("Senha deve ter pelo menos 8 caracteres", 400)
            from app.services.auth_service import hash_password

            updates["password_hash"] = hash_password(pw)

        user = user_repo.update(user, **updates)
        return success_response({"user": user.to_dict()})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# DELETE /api/users/<id> — soft delete (desativa)
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_user(user_id):
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)

        current = request.current_user
        if current["user_id"] == user_id:
            return error_response("Não é possível desativar o próprio usuário", 400)

        user_repo.soft_delete(user)
        return success_response({}, message="Usuário desativado")
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# DELETE /api/users/<id>/hard — apaga definitivamente (anonimiza)
# Libera email e nome para reuso. Exige usuário já inativo (fluxo 2 passos).
# Não remove a linha — anonimiza para preservar FKs históricas (pedidos, ledger).
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/hard", methods=["DELETE"])
@require_auth(roles=["admin"])
def hard_delete_user(user_id):
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)

        current = request.current_user
        if current["user_id"] == user_id:
            return error_response("Não é possível apagar o próprio usuário", 400)

        if user.is_active:
            return error_response("Desative o usuário antes de apagar definitivamente", 400)

        # Já é um tombstone? Idempotente.
        if (user.email or "").startswith("deleted_"):
            return success_response({}, message="Usuário já apagado")

        user_repo.anonymize(user)
        return success_response({}, message="Usuário apagado · email e nome liberados")
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /api/users/<id>/reactivate — reativa usuário desativado
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/reactivate", methods=["POST"])
@require_auth(roles=["admin"])
def reactivate_user(user_id):
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)
        if (user.email or "").startswith("deleted_"):
            return error_response("Usuário foi apagado e não pode ser reativado", 400)
        if user.is_active:
            return success_response({"user": user.to_dict()}, message="Já está ativo")
        user_repo.reactivate(user)
        return success_response({"user": user.to_dict()}, message="Usuário reativado")
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# GET /api/users/<id>/config — payroll + commission config
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/config", methods=["GET"])
@require_auth(roles=["admin"])
def get_user_config(user_id):
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)

        payroll = user_repo.get_payroll_configs(user_id)
        commission = user_repo.get_commission_configs(user_id)

        return success_response(
            {
                "user": user.to_dict(),
                "payroll": [p.to_dict() for p in payroll],
                "commission": [c.to_dict() for c in commission],
            }
        )
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# PUT /api/users/<id>/payroll — configura remuneração fixa
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/payroll", methods=["PUT"])
@require_auth(roles=["admin"])
def update_payroll(user_id):
    """
    Body pode ser uma lista de configs ou um único objeto:
      [{"category": "fixo_semanal", "label": "Salário", "amount": 500, "frequency": "semanal"}, ...]
    """
    try:
        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)

        data = request.get_json() or {}
        configs_data = data if isinstance(data, list) else [data]

        results = []
        for cfg_data in configs_data:
            if not cfg_data.get("category") or cfg_data.get("amount") is None:
                return error_response("category e amount são obrigatórios em cada config", 400)

            try:
                amount_val = float(cfg_data.get("amount"))
            except (TypeError, ValueError):
                return error_response("amount deve ser numérico", 400)
            if amount_val < 0:
                return error_response("amount não pode ser negativo", 400)

            frequency = (cfg_data.get("frequency") or "semanal").strip().lower()
            payment_day = cfg_data.get("payment_day")
            if payment_day is not None:
                try:
                    payment_day_int = int(payment_day)
                except (TypeError, ValueError):
                    return error_response("payment_day deve ser inteiro 0-6", 400)
                if payment_day_int < 0 or payment_day_int > 6:
                    return error_response("payment_day deve estar entre 0 (Seg) e 6 (Dom)", 400)
            elif frequency == "semanal":
                return error_response(
                    "payment_day é obrigatório para configs semanais (0=Seg ... 6=Dom)", 400
                )

            cfg = user_repo.upsert_payroll_config(user_id, cfg_data)
            results.append(cfg.to_dict())

        return success_response({"payroll": results})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# DELETE /api/users/<id>/payroll/<config_id> — remove config de remuneração
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/payroll/<int:config_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_payroll(user_id, config_id):
    try:
        ok = user_repo.deactivate_payroll_config(config_id)
        if not ok:
            return error_response("Config não encontrada", 404)
        return success_response({}, message="Remuneração removida")
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# PUT /api/users/<id>/commission — configura comissões
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/commission", methods=["PUT"])
@require_auth(roles=["admin"])
def update_commission(user_id):
    """
    Body pode ser lista ou objeto:
      [{"fonte_pedido_id": 10, "rate": 0.03}, ...]
      [{"source": "whatsapp", "rate": 0.03}, ...]  # legado
    """
    try:
        from app.models.fonte_pedido import FontePedido

        user = user_repo.get_by_id(user_id)
        if not user or not _in_current_store(user):
            return error_response("Usuário não encontrado", 404)

        data = request.get_json() or {}
        configs_data = data if isinstance(data, list) else [data]

        results = []
        for cfg_data in configs_data:
            fonte_pedido_id = cfg_data.get("fonte_pedido_id")
            source = (cfg_data.get("source") or "").strip()

            if fonte_pedido_id is not None:
                try:
                    fonte_pedido_id = int(fonte_pedido_id)
                except (TypeError, ValueError):
                    return error_response("fonte_pedido_id inválido", 400)

                fonte = FontePedido.query.filter(FontePedido.id == fonte_pedido_id).first()
                if not fonte:
                    return error_response(
                        f"fonte_pedido_id '{fonte_pedido_id}' não encontrado", 404
                    )

            if fonte_pedido_id is None and not source:
                return error_response("Informe fonte_pedido_id ou source", 400)
            rate = cfg_data.get("rate")
            if rate is None:
                return error_response("rate é obrigatório", 400)
            try:
                rate_val = float(rate)
            except (TypeError, ValueError):
                return error_response("rate deve ser numérico", 400)
            if rate_val < 0:
                return error_response("rate não pode ser negativo", 400)
            if rate_val > 1:
                return error_response(
                    "rate deve ser decimal (ex: 0.05 para 5%); valores >1 são inválidos", 400
                )
            payload = {
                "source": source,
                "rate": rate,
                "fonte_pedido_id": fonte_pedido_id,
            }
            cfg = user_repo.upsert_commission_config(user_id, payload)
            results.append(cfg.to_dict())

        return success_response({"commission": results})
    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# DELETE /api/users/<id>/commission/<config_id> — remove comissão
# ---------------------------------------------------------------------------
@users_bp.route("/<int:user_id>/commission/<int:config_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_commission(user_id, config_id):
    try:
        ok = user_repo.deactivate_commission_config(config_id)
        if not ok:
            return error_response("Config não encontrada", 404)
        return success_response({}, message="Comissão removida")
    except Exception as e:
        return error_response(str(e), 500)
