import json
import os
from datetime import date

from flask import Blueprint, g, jsonify, request

from app import db
from app.middleware import requires_edit_auth, requires_role
from app.services.integration_settings_service import (
    default_store,
    get_or_create_settings,
    get_settings,
    serialize_settings,
    update_settings,
)
from app.services.taxa_cartao import taxa_cartao_service
from app.services.taxa_entrega import taxa_entrega_service

config_bp = Blueprint("config", __name__, url_prefix="/api/config")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
META_FATURAMENTO_PATH = os.path.join(BASE_DIR, "config", "meta_faturamento.json")


def _current_store():
    """Loja autenticada da request (multi-tenant).

    Usa `g.current_store` populado pela resolução de identidade. Só cai em
    `default_store()` como salvaguarda de transição quando não há loja no contexto
    (ex.: caminho legado Basic Auth), nunca para o fluxo JWT normal.
    """
    store = getattr(g, "current_store", None)
    if store is not None:
        return store
    return default_store()


@config_bp.route("/integrations", methods=["GET"])
@requires_role("admin")
def get_integration_settings():
    """Retorna credenciais da loja autenticada com segredos sempre mascarados."""
    try:
        store = _current_store()
        settings = get_settings(store.id)
        return jsonify(
            {
                "success": True,
                "config": serialize_settings(store, settings),
            }
        )
    except RuntimeError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        return jsonify({"success": False, "error": "Falha ao ler as integracoes"}), 500


@config_bp.route("/integrations", methods=["PUT"])
@requires_role("admin")
def update_integration_settings():
    """Atualiza configuracoes do tenant sem regravar valores mascarados."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Payload JSON invalido"}), 400
    try:
        store = _current_store()
        settings = get_or_create_settings(store.id)
        update_settings(settings, data)
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": "Integracoes atualizadas",
                "config": serialize_settings(store, settings),
            }
        )
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 400
    except RuntimeError as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Falha ao salvar as integracoes"}), 500


def _load_meta_faturamento() -> dict:
    if not os.path.exists(META_FATURAMENTO_PATH):
        return {"meta_mensal": {}}
    try:
        with open(META_FATURAMENTO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    if "meta_mensal" not in data or not isinstance(data.get("meta_mensal"), dict):
        data["meta_mensal"] = {}
    return data


def _save_meta_faturamento(data: dict) -> None:
    os.makedirs(os.path.dirname(META_FATURAMENTO_PATH), exist_ok=True)
    with open(META_FATURAMENTO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@config_bp.route("/taxa-entrega", methods=["GET"])
@requires_edit_auth
def get_taxa_entrega_config():
    """Retorna a configuração atual da taxa de entrega"""
    try:
        # Força recarregamento do arquivo
        config = taxa_entrega_service._carregar_config()
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/taxa-entrega", methods=["POST"])
@requires_edit_auth
def update_taxa_entrega_config():
    """Atualiza a configuração da taxa de entrega"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Dados não fornecidos"}), 400

        # Validar dados (simples)
        if "tipo" not in data:
            return jsonify({"success": False, "error": "Campo 'tipo' obrigatório"}), 400

        # Salvar no arquivo
        config_path = taxa_entrega_service.config_path

        # Garantir que diretório existe
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # Recarregar serviço
        taxa_entrega_service.config = taxa_entrega_service._carregar_config()

        return jsonify(
            {"success": True, "message": "Configuração atualizada com sucesso", "config": data}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/meta-faturamento", methods=["GET"])
@requires_edit_auth
def get_meta_faturamento():
    """Retorna a meta de faturamento para um mês (YYYY-MM)."""
    try:
        mes = request.args.get("mes") or date.today().strftime("%Y-%m")
        data = _load_meta_faturamento()
        valor = data.get("meta_mensal", {}).get(mes)
        return jsonify({"success": True, "mes": mes, "valor": valor})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/meta-faturamento", methods=["POST"])
@requires_edit_auth
def update_meta_faturamento():
    """Atualiza a meta de faturamento para um mês (YYYY-MM)."""
    try:
        payload = request.get_json() or {}
        mes = payload.get("mes")
        valor = payload.get("valor")
        if not mes:
            return jsonify({"success": False, "error": "Campo 'mes' obrigatório (YYYY-MM)"}), 400
        if valor is None:
            return jsonify({"success": False, "error": "Campo 'valor' obrigatório"}), 400
        try:
            valor_num = float(valor)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Campo 'valor' inválido"}), 400

        data = _load_meta_faturamento()
        data.setdefault("meta_mensal", {})
        data["meta_mensal"][mes] = valor_num
        _save_meta_faturamento(data)

        return jsonify({"success": True, "mes": mes, "valor": valor_num})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/taxa-cartao", methods=["GET"])
@requires_edit_auth
def get_taxa_cartao_config():
    """Retorna a configuração atual da taxa de cartão (débito + crédito)."""
    try:
        taxa_cartao_service.recarregar()
        return jsonify({"success": True, "config": taxa_cartao_service.config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/taxa-cartao", methods=["POST"])
@requires_edit_auth
def update_taxa_cartao_config():
    """Atualiza a configuração da taxa de cartão."""
    try:
        data = request.get_json() or {}

        if "debito_pct" not in data or "credito" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Campos 'debito_pct' e 'credito' obrigatórios",
                    }
                ),
                400,
            )

        try:
            debito_pct = float(data["debito_pct"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "debito_pct inválido"}), 400
        if debito_pct < 0 or debito_pct > 100:
            return (
                jsonify({"success": False, "error": "debito_pct fora do intervalo 0-100"}),
                400,
            )

        credito_raw = data["credito"]
        if not isinstance(credito_raw, list) or not credito_raw:
            return (
                jsonify({"success": False, "error": "credito deve ser uma lista não-vazia"}),
                400,
            )

        credito_validado = []
        for item in credito_raw:
            try:
                parcelas = int(item["parcelas"])
                taxa_pct = float(item["taxa_pct"])
            except (KeyError, TypeError, ValueError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Cada faixa precisa de 'parcelas' (int) e 'taxa_pct' (float)",
                        }
                    ),
                    400,
                )
            if parcelas < 1 or parcelas > 24:
                return (
                    jsonify({"success": False, "error": "parcelas fora do intervalo 1-24"}),
                    400,
                )
            if taxa_pct < 0 or taxa_pct > 100:
                return (
                    jsonify({"success": False, "error": "taxa_pct fora do intervalo 0-100"}),
                    400,
                )
            credito_validado.append({"parcelas": parcelas, "taxa_pct": taxa_pct})

        credito_validado.sort(key=lambda f: f["parcelas"])
        novo = {"debito_pct": debito_pct, "credito": credito_validado}

        os.makedirs(os.path.dirname(taxa_cartao_service.config_path), exist_ok=True)
        with open(taxa_cartao_service.config_path, "w", encoding="utf-8") as f:
            json.dump(novo, f, indent=4, ensure_ascii=False)

        taxa_cartao_service.recarregar()

        return jsonify({"success": True, "message": "Configuração atualizada", "config": novo})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
