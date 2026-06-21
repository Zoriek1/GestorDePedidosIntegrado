# -*- coding: utf-8 -*-
"""Mapeamento financeiro Gestor -> Bling."""

from app import db
from app.models.pedido import datetime_now_brazil


class BlingPaymentMapping(db.Model):
    __tablename__ = "bling_payment_mapping"

    id = db.Column(db.Integer, primary_key=True)
    gestor_payment_label = db.Column(db.String(80), nullable=False, unique=True, index=True)
    bling_payment_method_id = db.Column(
        db.Integer, db.ForeignKey("bling_payment_methods.id"), nullable=True, index=True
    )
    bling_financial_account_id = db.Column(
        db.Integer, db.ForeignKey("bling_financial_accounts.id"), nullable=True, index=True
    )
    bling_category_id = db.Column(
        db.Integer, db.ForeignKey("bling_categories.id"), nullable=True, index=True
    )
    applies_to_receivable = db.Column(db.Boolean, nullable=False, default=True)
    applies_to_payable = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil)

    payment_method = db.relationship("BlingPaymentMethod", lazy="joined")
    financial_account = db.relationship("BlingFinancialAccount", lazy="joined")
    category = db.relationship("BlingCategory", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "gestor_payment_label": self.gestor_payment_label,
            "bling_payment_method_id": self.bling_payment_method_id,
            "bling_financial_account_id": self.bling_financial_account_id,
            "bling_category_id": self.bling_category_id,
            "applies_to_receivable": self.applies_to_receivable,
            "applies_to_payable": self.applies_to_payable,
            "active": self.active,
            "payment_method": self.payment_method.to_dict() if self.payment_method else None,
            "financial_account": self.financial_account.to_dict()
            if self.financial_account
            else None,
            "category": self.category.to_dict() if self.category else None,
        }
