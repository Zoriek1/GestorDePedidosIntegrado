# -*- coding: utf-8 -*-
"""
UserRepository — CRUD de usuários, payroll_config e commission_config
"""
from typing import List, Optional

from app import db
from app.models.user import CommissionConfig, PayrollConfig, User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    # ------------------------------------------------------------------
    # User queries
    # ------------------------------------------------------------------

    def get_by_email(self, email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

    def get_active_by_role(self, role: str) -> List[User]:
        return User.query.filter_by(role=role, is_active=True).all()

    def get_all_active(self) -> List[User]:
        return User.query.filter_by(is_active=True).order_by(User.name).all()

    def soft_delete(self, user: User) -> User:
        user.is_active = False
        db.session.commit()
        return user

    # ------------------------------------------------------------------
    # PayrollConfig
    # ------------------------------------------------------------------

    def get_payroll_configs(self, user_id: int) -> List[PayrollConfig]:
        return PayrollConfig.query.filter_by(user_id=user_id, is_active=True).all()

    def upsert_payroll_config(self, user_id: int, data: dict) -> PayrollConfig:
        """
        Atualiza config existente (mesmo category) ou cria nova.
        Desativa configs antigas com a mesma category antes de criar.
        """
        category = data.get("category")
        if category:
            # Desativar configs anteriores com a mesma category
            existing = PayrollConfig.query.filter_by(
                user_id=user_id, category=category, is_active=True
            ).all()
            for cfg in existing:
                cfg.is_active = False

        new_cfg = PayrollConfig(
            user_id=user_id,
            category=data.get("category", "custom"),
            label=data.get("label", ""),
            amount=float(data.get("amount", 0)),
            frequency=data.get("frequency", "semanal"),
            is_active=True,
        )
        db.session.add(new_cfg)
        db.session.commit()
        return new_cfg

    def deactivate_payroll_config(self, config_id: int) -> bool:
        cfg = PayrollConfig.query.get(config_id)
        if not cfg:
            return False
        cfg.is_active = False
        db.session.commit()
        return True

    # ------------------------------------------------------------------
    # CommissionConfig
    # ------------------------------------------------------------------

    def get_commission_configs(self, user_id: int) -> List[CommissionConfig]:
        return CommissionConfig.query.filter_by(user_id=user_id, is_active=True).all()

    def get_active_commission(self, user_id: int, source: str) -> Optional[CommissionConfig]:
        return CommissionConfig.query.filter_by(
            user_id=user_id, source=source, is_active=True
        ).first()

    def upsert_commission_config(self, user_id: int, data: dict) -> CommissionConfig:
        source = data.get("source")
        if source:
            existing = CommissionConfig.query.filter_by(
                user_id=user_id, source=source, is_active=True
            ).all()
            for cfg in existing:
                cfg.is_active = False

        new_cfg = CommissionConfig(
            user_id=user_id,
            source=data.get("source", ""),
            rate=float(data.get("rate", 0)),
            is_active=True,
        )
        db.session.add(new_cfg)
        db.session.commit()
        return new_cfg

    def deactivate_commission_config(self, config_id: int) -> bool:
        cfg = CommissionConfig.query.get(config_id)
        if not cfg:
            return False
        cfg.is_active = False
        db.session.commit()
        return True
