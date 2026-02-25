# -*- coding: utf-8 -*-
"""
Serviço de Push Notifications via Web Push (VAPID).

Envia notificações para todos os dispositivos inscritos.
Limpa automaticamente inscrições inválidas (410 Gone).
"""
import json
import logging
import threading
from typing import Optional

from pywebpush import WebPushException, webpush

from app import db
from app.config import Config
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def _get_vapid_claims() -> dict:
    return {"sub": Config.VAPID_CLAIMS_EMAIL}


def format_delivery_datetime(dia_entrega, horario: Optional[str] = None) -> str:
    """
    Formata data e hora de entrega para exibição em notificações.

    Args:
        dia_entrega: Objeto date ou string no formato YYYY-MM-DD
        horario: String com horário (ex: "14:00" ou "14:00 - 18:00")

    Returns:
        String formatada: "DD/MM/YYYY às HH:MM" ou "DD/MM/YYYY - HH:MM - HH:MM" ou apenas "DD/MM/YYYY"
    """
    if not dia_entrega:
        return ""

    # Converter para date se for string
    if isinstance(dia_entrega, str):
        try:
            from datetime import datetime

            dia_entrega = datetime.strptime(dia_entrega, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return ""

    # Formatar data como DD/MM/YYYY
    data_formatada = dia_entrega.strftime("%d/%m/%Y")

    if not horario or not horario.strip():
        return data_formatada

    horario_limpo = horario.strip()

    # Se tem intervalo de horário (ex: "14:00 - 18:00")
    if " - " in horario_limpo:
        partes = horario_limpo.split(" - ")
        if len(partes) == 2:
            inicio = partes[0].strip()
            fim = partes[1].strip()
            return f"{data_formatada} - {inicio} às {fim}"

    # Horário único
    return f"{data_formatada} às {horario_limpo}"


def send_push_to_all(
    title: str,
    body: str,
    url: Optional[str] = "/",
    icon: Optional[str] = "/pwa-192x192.png",
) -> dict:
    """
    Envia push notification para TODAS as inscrições ativas.

    Args:
        title: Título da notificação.
        body: Corpo da notificação.
        url: URL para abrir ao clicar na notificação.
        icon: Caminho do ícone.

    Returns:
        dict com contadores: sent, failed, removed.
    """
    if not Config.VAPID_PRIVATE_KEY or not Config.VAPID_PUBLIC_KEY:
        logger.warning("[Push] VAPID keys não configuradas. Notificação ignorada.")
        return {"sent": 0, "failed": 0, "removed": 0, "error": "vapid_not_configured"}

    subscriptions = PushSubscription.query.all()
    if not subscriptions:
        logger.info("[Push] Nenhuma inscrição ativa. Nada a enviar.")
        return {"sent": 0, "failed": 0, "removed": 0}

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url,
            "icon": icon,
        },
        ensure_ascii=False,
    )

    sent = 0
    failed = 0
    to_remove = []

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            },
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=Config.VAPID_PRIVATE_KEY,
                vapid_claims=_get_vapid_claims(),
            )
            sent += 1
        except WebPushException as ex:
            status_code = getattr(ex, "response", None)
            if status_code is not None:
                status_code = getattr(status_code, "status_code", None)

            if status_code in (404, 410):
                # Subscription inválida ou expirada — marcar para remoção
                to_remove.append(sub.id)
                logger.info(
                    "[Push] Subscription removida (status %s): %s...",
                    status_code,
                    sub.endpoint[:60],
                )
            else:
                failed += 1
                logger.warning(
                    "[Push] Falha ao enviar para %s...: %s",
                    sub.endpoint[:60],
                    ex,
                )
        except Exception as ex:
            failed += 1
            logger.warning("[Push] Erro inesperado: %s", ex)

    # Remover subscriptions inválidas
    removed = 0
    if to_remove:
        removed = PushSubscription.query.filter(PushSubscription.id.in_(to_remove)).delete(
            synchronize_session="fetch"
        )
        db.session.commit()

    result = {"sent": sent, "failed": failed, "removed": removed}
    logger.info("[Push] Resultado: %s", result)
    return result


def send_push_to_all_async(
    app,
    title: str,
    body: str,
    url: Optional[str] = "/",
    icon: Optional[str] = "/pwa-192x192.png",
) -> None:
    """
    Versão assíncrona (background thread) de send_push_to_all.

    Usa uma thread separada para não bloquear a resposta HTTP.
    Requer a instância real do Flask (não o proxy current_app).
    """

    def _worker():
        with app.app_context():
            try:
                send_push_to_all(title=title, body=body, url=url, icon=icon)
            except Exception:
                logger.exception("[Push] Erro no envio assíncrono de push.")

    thread = threading.Thread(target=_worker, name="PushNotify", daemon=True)
    thread.start()
