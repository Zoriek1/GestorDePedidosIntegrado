# -*- coding: utf-8 -*-
"""
UserRepository — CRUD de usuários, payroll_config e commission_config
"""
from typing import List, Optional

from app import db
from app.models.fonte_pedido import FontePedido
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

    def get_active_by_name(self, name: str) -> List[User]:
        """Usuários ativos cujo nome bate (case-insensitive). Usado para checar
        unicidade de nome ao criar/editar e para o login por nome."""
        return User.query.filter(
            db.func.lower(User.name) == (name or "").strip().lower(),
            User.is_active == True,  # noqa: E712
        ).all()

    def get_active_by_role(self, role: str) -> List[User]:
        return User.query.filter_by(role=role, is_active=True).all()

    def get_all_active(self) -> List[User]:
        return User.query.filter_by(is_active=True).order_by(User.name).all()

    def get_all(self) -> List[User]:
        return User.query.order_by(User.is_active.desc(), User.name).all()

    def soft_delete(self, user: User) -> User:
        user.is_active = False
        db.session.commit()
        return user

    def reactivate(self, user: User) -> User:
        user.is_active = True
        db.session.commit()
        return user

    def anonymize(self, user: User) -> User:
        """
        Anonimiza um usuário desativado para liberar email e nome para reuso.
        A linha é mantida para preservar referências em pedidos e ledger entries.
        """
        from datetime import datetime

        ts = int(datetime.utcnow().timestamp())
        user.name = "Usuário removido"
        user.email = f"deleted_{user.id}_{ts}@deleted.local"
        user.is_active = False
        # Invalida a senha: força reset se de alguma forma alguém reativar via DB direto
        user.password_hash = "!deleted"
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

        payment_day = data.get("payment_day")
        new_cfg = PayrollConfig(
            user_id=user_id,
            category=data.get("category", "custom"),
            label=data.get("label", ""),
            amount=float(data.get("amount", 0)),
            frequency=data.get("frequency", "semanal"),
            payment_day=int(payment_day) if payment_day is not None else None,
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

    def get_active_commission(
        self,
        user_id: int,
        source: str | None = None,
        fonte_pedido_id: int | None = None,
    ) -> Optional[CommissionConfig]:
        # 1) Preferencial: configuração vinculada à fonte real
        if fonte_pedido_id:
            config = CommissionConfig.query.filter_by(
                user_id=user_id,
                fonte_pedido_id=fonte_pedido_id,
                is_active=True,
            ).first()
            if config:
                return config

        # 2) Fallback legado: source string
        if source:
            return CommissionConfig.query.filter_by(
                user_id=user_id,
                source=source,
                is_active=True,
            ).first()

        return None

    def _resolve_source_from_fonte(self, fonte_pedido_id: int | None) -> str | None:
        if not fonte_pedido_id:
            return None
        fonte = FontePedido.query.filter(FontePedido.id == fonte_pedido_id).first()
        if not fonte or not fonte.nome:
            return None

        # Mantém a convenção usada em commission_config.source
        import unicodedata

        nfkd = unicodedata.normalize("NFD", fonte.nome)
        ascii_name = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
        return ascii_name.lower().strip().replace(" ", "_")

    def upsert_commission_config(self, user_id: int, data: dict) -> CommissionConfig:
        """
        Upsert atômico de CommissionConfig.

        Os índices parciais únicos (ux_comm_user_fonte_active,
        ux_comm_user_source_active) garantem no nível do banco que existe no
        máximo uma config ativa por (user_id, fonte_pedido_id) ou
        (user_id, source). Em caso de race condition, o segundo INSERT levanta
        IntegrityError e o tratador relê o estado e retenta a desativação.
        """
        from sqlalchemy.exc import IntegrityError

        fonte_pedido_id = data.get("fonte_pedido_id")
        try:
            fonte_pedido_id = int(fonte_pedido_id) if fonte_pedido_id is not None else None
        except (TypeError, ValueError):
            fonte_pedido_id = None

        source = (data.get("source") or "").strip() or None
        if not source:
            source = self._resolve_source_from_fonte(fonte_pedido_id)
        source = source or ""

        rate_value = float(data.get("rate", 0))

        for attempt in range(2):  # 1 retry após IntegrityError
            try:
                with db.session.begin_nested():
                    if fonte_pedido_id is not None:
                        existing = CommissionConfig.query.filter_by(
                            user_id=user_id,
                            fonte_pedido_id=fonte_pedido_id,
                            is_active=True,
                        ).all()
                    else:
                        existing = CommissionConfig.query.filter_by(
                            user_id=user_id,
                            source=source,
                            is_active=True,
                        ).all()
                    for cfg in existing:
                        cfg.is_active = False
                    db.session.flush()

                    new_cfg = CommissionConfig(
                        user_id=user_id,
                        fonte_pedido_id=fonte_pedido_id,
                        source=source,
                        rate=rate_value,
                        is_active=True,
                    )
                    db.session.add(new_cfg)
                    db.session.flush()
                db.session.commit()
                return new_cfg
            except IntegrityError:
                db.session.rollback()
                if attempt == 1:
                    raise
                # próxima iteração relê o estado e tenta novamente
                continue

        # inalcançável: ou retorna no try, ou propaga no raise
        raise RuntimeError("upsert_commission_config: estado inesperado")

    def deactivate_commission_config(self, config_id: int) -> bool:
        cfg = CommissionConfig.query.get(config_id)
        if not cfg:
            return False
        cfg.is_active = False
        db.session.commit()
        return True
