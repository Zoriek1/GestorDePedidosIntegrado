import json
import os
import re
from datetime import date

from flask import Blueprint, g, jsonify, request

from app import db
from app.middleware import requires_edit_auth, requires_role
from app.models.integration_validation_log import IntegrationValidationLog
from app.services.integration_settings_service import (
    ALLOWED_FIELDS,
    BOOLEAN_FIELDS,
    SECRET_FIELDS,
    STRING_FIELDS,
    channel_fields,
    channel_supports_patch,
    default_store,
    get_or_create_settings,
    get_settings,
    is_known_channel,
    is_masked,
    serialize_settings,
    update_settings,
)
from app.services.integration_validation import validate as validate_field_value
from app.services.integration_validation.lock import store_lock
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
    data = _parse_json_body()
    if data is None:
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


# =============================================================================
# F6/E0 — Grid de Integracoes: PATCH/validate/GET validation por canal/campo
# =============================================================================


def _validate_field_for_channel(channel: str, field: str) -> str | None:
    """Retorna None se (channel, field) eh patch-avel; senao mensagem de erro."""
    if not is_known_channel(channel):
        return f"Canal desconhecido: {channel}"
    if not channel_supports_patch(channel):
        return f"Canal sem campos de configuracao (OAuth): {channel}"
    if field not in channel_fields(channel):
        return f"Campo '{field}' nao pertence ao canal '{channel}'"
    if field not in ALLOWED_FIELDS:
        return f"Campo nao permitido: {field}"
    return None


def _normalize_field_value(field: str, value) -> tuple[object, str | None]:
    """Converte o payload bruto no valor a persistir, ou erro de validacao."""
    if value is None:
        return None, None
    if field in BOOLEAN_FIELDS:
        if not isinstance(value, bool):
            return None, f"{field} deve ser booleano"
        return value, None
    if field in STRING_FIELDS:
        if not isinstance(value, str):
            return None, f"{field} deve ser texto ou null"
        if _has_control_chars(value):
            return None, f"{field} contém caracteres inválidos"
        normalized = value.strip() or None
        if normalized and len(normalized) > STRING_FIELDS[field]:
            return None, f"{field} excede {STRING_FIELDS[field]} caracteres"
        if field == "loja_cep" and normalized and not re.fullmatch(r"\d{5}-?\d{3}", normalized):
            return None, "loja_cep deve estar no formato 00000-000"
        if field == "loja_cep" and normalized and "-" not in normalized:
            normalized = f"{normalized[:5]}-{normalized[5:]}"
        return normalized, None
    if field in SECRET_FIELDS:
        if isinstance(value, str) and is_masked(value):
            # Cliente ecoando a mascara -> sem alteracao.
            return "__KEEP__", None
        if not isinstance(value, str):
            return None, f"{field} deve ser texto ou null"
        if _has_control_chars(value):
            return None, f"{field} contém caracteres inválidos"
        normalized = value.strip() or None
        return normalized, None
    return None, f"Campo nao permitido: {field}"


def _has_control_chars(value: str) -> bool:
    """Rejeita bytes de controle (< 0x20) e DEL (0x7f).

    Defesa contra log injection (\\n, \\r) e smuggling. Tabs (\\t) e espaços
    sao aceitos normalmente.
    """
    return any(ord(c) < 32 or ord(c) == 127 for c in value)


def _reset_validation_log(store_id: int, channel: str) -> None:
    """Apaga o historico de validacao de um canal apos PATCH."""
    IntegrationValidationLog.query.filter_by(store_ref_id=store_id, channel=channel).delete()


def _append_validation_log(
    store_id: int, channel: str, field: str | None, ok: bool, error: str | None
) -> IntegrationValidationLog:
    entry = IntegrationValidationLog(
        store_ref_id=store_id,
        channel=channel,
        field=field,
        ok=ok,
        error=error,
    )
    db.session.add(entry)
    return entry


def _field_saved_value(settings, field: str):
    """Retorna o valor persistido (secret descriptografado) de um campo."""
    if field in SECRET_FIELDS:
        return settings.get_secret(field) if settings else None
    return getattr(settings, field, None) if settings else None


def _parse_json_body() -> dict | None:
    """Aceita o body como JSON mesmo sem Content-Type: application/json.

    O `fetch()` do browser não seta Content-Type automaticamente quando o body
    é uma string JSON, então o Flask retorna 400 "Campo 'value' obrigatorio"
    no PATCH. Como fallback, lemos o body bruto e tentamos parsear como JSON
    se começar com `{` ou `[`.
    """
    data = request.get_json(silent=True)
    if data is None:
        raw = (request.get_data(as_text=True) or "").strip()
        if not raw.startswith("{"):
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            return None
    return data if isinstance(data, dict) else None


@config_bp.route("/integrations/<channel>/<field>", methods=["PATCH"])
@requires_role("admin")
def patch_integration_field(channel: str, field: str):
    """Grava um unico campo por canal. `null` remove. Reseta `validation_log`."""
    err = _validate_field_for_channel(channel, field)
    if err:
        return jsonify({"success": False, "error": err}), 400

    data = _parse_json_body() or {}
    if "value" not in data:
        return jsonify({"success": False, "error": "Campo 'value' obrigatorio"}), 400
    normalized, norm_err = _normalize_field_value(field, data["value"])
    if norm_err:
        return jsonify({"success": False, "error": norm_err}), 400

    store = _current_store()
    try:
        with store_lock(store.id):
            settings = get_or_create_settings(store.id)
            if normalized == "__KEEP__":
                # Cliente ecoou mascara: nada a fazer.
                pass
            else:
                if field in SECRET_FIELDS:
                    settings.set_secret(field, normalized)
                else:
                    setattr(settings, field, normalized)
                _reset_validation_log(store.id, channel)
            db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": "Campo atualizado",
                "config": serialize_settings(store, settings),
            }
        )
    except RuntimeError as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Falha ao salvar o campo"}), 500


@config_bp.route("/integrations/<channel>/<field>/validate", methods=["POST"])
@requires_role("admin")
def validate_integration_field(channel: str, field: str):
    """Valida um campo isolado (formato e/ou rede). Grava em validation_log."""
    err = _validate_field_for_channel(channel, field)
    if err:
        return jsonify({"success": False, "error": err}), 400

    data = _parse_json_body() or {}
    raw_value = data.get("value")

    store = _current_store()
    try:
        with store_lock(store.id):
            settings = get_or_create_settings(store.id)
            # Se cliente nao enviou valor, usa o persistido (secrets descriptografados).
            if raw_value is None or (isinstance(raw_value, str) and raw_value == ""):
                raw_value = _field_saved_value(settings, field)
            if field in SECRET_FIELDS and isinstance(raw_value, str) and is_masked(raw_value):
                raw_value = _field_saved_value(settings, field)

            ok, error_msg = validate_field_value(channel, field, raw_value)
            entry = _append_validation_log(store.id, channel, field, ok, error_msg)
            db.session.commit()
            return jsonify(
                {
                    "success": True,
                    "ok": ok,
                    "error": error_msg,
                    "last_test_at": entry.validated_at.isoformat() if entry.validated_at else None,
                }
            )
    except RuntimeError as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Falha ao validar o campo"}), 500


@config_bp.route("/integrations/validation", methods=["GET"])
@requires_role("admin")
def list_integration_validation():
    """Lista o ultimo status de validacao por canal para a loja atual."""
    store = _current_store()
    channel = request.args.get("channel")
    try:
        q = IntegrationValidationLog.query.filter_by(store_ref_id=store.id)
        if channel:
            q = q.filter_by(channel=channel)
        entries = q.order_by(IntegrationValidationLog.validated_at.desc()).limit(100).all()
        return jsonify(
            {
                "success": True,
                "entries": [e.to_dict() for e in entries],
            }
        )
    except RuntimeError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        return jsonify({"success": False, "error": "Falha ao ler validacoes"}), 500


@config_bp.route("/integrations/<channel>/status", methods=["GET"])
@requires_role("admin")
def channel_validation_status(channel: str):
    """Atalho: retorna o ultimo `ok` por canal agregado (sem filtrar por campo)."""
    if not is_known_channel(channel):
        return jsonify({"success": False, "error": f"Canal desconhecido: {channel}"}), 400

    store = _current_store()
    try:
        latest = (
            IntegrationValidationLog.query.filter_by(store_ref_id=store.id, channel=channel)
            .order_by(IntegrationValidationLog.validated_at.desc())
            .first()
        )
        return jsonify(
            {
                "success": True,
                "channel": channel,
                "ok": bool(latest.ok) if latest else None,
                "last_test_at": latest.validated_at.isoformat() if latest else None,
                "error": latest.error if latest else None,
            }
        )
    except RuntimeError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        return jsonify({"success": False, "error": "Falha ao ler status do canal"}), 500


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
        data = _parse_json_body()
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
        payload = _parse_json_body() or {}
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
        data = _parse_json_body() or {}

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
