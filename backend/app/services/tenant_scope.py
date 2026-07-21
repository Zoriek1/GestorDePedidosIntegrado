# -*- coding: utf-8 -*-
"""Escopo automático de leitura para entidades pertencentes a uma loja."""

from __future__ import annotations

from flask import g, has_request_context
from sqlalchemy import Column, ForeignKey, Integer, event, false, or_
from sqlalchemy.orm import Session, declared_attr, with_loader_criteria


class TenantScoped:
    """Marcador para models que possuem ``store_ref_id``."""

    __tenant_scoped__ = True

    @declared_attr
    def store_ref_id(cls):  # noqa: N805 - protocolo de mixin declarativo
        return Column(
            Integer,
            ForeignKey("stores.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )


_registered = False


def register_tenant_scope() -> None:
    """Registra uma única vez o filtro global de SELECT da SQLAlchemy."""
    global _registered
    if _registered:
        return

    @event.listens_for(Session, "do_orm_execute")
    def _apply_tenant_scope(execute_state):
        if not execute_state.is_select:
            return
        if execute_state.execution_options.get("include_all_tenants"):
            return
        if not has_request_context():
            return

        tenant_id = getattr(g, "tenant_store_id", None)
        multi = bool(getattr(g, "tenant_multi", False))

        # Em multi-store, uma consulta sem identidade nunca pode degradar para
        # uma leitura global. Rotas públicas que precisam de dados usam o escape
        # hatch e um identificador assinado/tenant explícito.
        if multi and tenant_id is None:
            criterion = lambda cls: false()  # noqa: E731
        elif tenant_id is not None and multi:
            criterion = lambda cls: cls.store_ref_id == tenant_id  # noqa: E731
        elif tenant_id is not None:
            criterion = lambda cls: or_(  # noqa: E731
                cls.store_ref_id == tenant_id,
                cls.store_ref_id.is_(None),
            )
        else:
            return

        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                TenantScoped,
                criterion,
                include_aliases=True,
                track_closure_variables=False,
            )
        )

    _registered = True
