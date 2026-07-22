# -*- coding: utf-8 -*-
"""Historico de validacoes por canal de integracao, isolado por loja.

Registra cada tentativa de validacao isolada (por campo ou canal inteiro) que
o frontend dispara no novo grid de Integracoes. Permite que a UI exiba o
estado "validado" (verde) ou "salvo mas nao validado" (amarelo) sem precisar
re-checar o provedor a cada render.
"""

from app import db
from app.models.pedido import datetime_now_brazil


class IntegrationValidationLog(db.Model):
    __tablename__ = "integration_validation_log"

    id = db.Column(db.Integer, primary_key=True)
    store_ref_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "stores.id",
            name="fk_integration_validation_log_store_ref_id_stores",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    channel = db.Column(db.String(64), nullable=False, index=True)
    field = db.Column(db.String(128), nullable=True)
    ok = db.Column(db.Boolean, nullable=False)
    error = db.Column(db.Text, nullable=True)
    validated_at = db.Column(db.DateTime, nullable=False, default=datetime_now_brazil, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "store_ref_id": self.store_ref_id,
            "channel": self.channel,
            "field": self.field,
            "ok": self.ok,
            "error": self.error,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<IntegrationValidationLog channel={self.channel!r} field={self.field!r} "
            f"ok={self.ok} @ {self.validated_at}>"
        )
