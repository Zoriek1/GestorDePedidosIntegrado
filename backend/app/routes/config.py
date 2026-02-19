import json
import os
from datetime import date

from flask import Blueprint, jsonify, request

from app.middleware import requires_auth, requires_edit_auth
from app.services.taxa_entrega import taxa_entrega_service

config_bp = Blueprint("config", __name__, url_prefix="/api/config")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
META_FATURAMENTO_PATH = os.path.join(BASE_DIR, "config", "meta_faturamento.json")


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
@requires_auth
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

        return jsonify({"success": True, "message": "Configuração atualizada com sucesso", "config": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@config_bp.route("/meta-faturamento", methods=["GET"])
@requires_auth
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
