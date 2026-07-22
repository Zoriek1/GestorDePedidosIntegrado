# -*- coding: utf-8 -*-
"""
Catálogo curado de arranjos (CAT-01).

Curado + promoção: a tabela começa vazia. A entrada livre no campo `produto` do pedido
continua sempre aceita; só entram no catálogo os nomes que a florista confirmar
(promover). `usos` ranqueia por frequência. A sugestão por similaridade usa pg_trgm no
Postgres (tolera typo); em SQLite/dev cai para substring LIKE.
"""
from app import db


class CatalogoArranjo(db.Model):
    __tablename__ = "catalogo_arranjos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.Text, nullable=False, unique=True)
    usos = db.Column(db.Integer, nullable=False, default=1)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome, "usos": self.usos}

    @staticmethod
    def sugerir(q, limit: int = 8):
        """Sugere nomes do catálogo por similaridade (PG) ou substring (SQLite)."""
        q = (q or "").strip()
        if not q:
            rows = CatalogoArranjo.query.order_by(CatalogoArranjo.usos.desc()).limit(limit).all()
            return [r.nome for r in rows]

        if db.engine.dialect.name == "postgresql":
            # `nome % :q` usa o limiar de similaridade trigram (tolera typo);
            # o OR por ILIKE garante o match de substring exata.
            sql = db.text(
                "SELECT nome FROM catalogo_arranjos "
                "WHERE nome % :q OR nome ILIKE :like "
                "ORDER BY similarity(nome, :q) DESC, usos DESC "
                "LIMIT :lim"
            )
            rows = db.session.execute(sql, {"q": q, "like": f"%{q}%", "lim": limit}).fetchall()
            return [r[0] for r in rows]

        # SQLite/outro: fallback por substring case-insensitive (sem typo tolerance).
        like = f"%{q.lower()}%"
        rows = (
            CatalogoArranjo.query.filter(db.func.lower(CatalogoArranjo.nome).like(like))
            .order_by(CatalogoArranjo.usos.desc())
            .limit(limit)
            .all()
        )
        return [r.nome for r in rows]

    @staticmethod
    def promover(nome):
        """Insere o nome no catálogo (usos=1) ou incrementa `usos` se já existir."""
        nome = (nome or "").strip()
        if not nome:
            return None
        existente = CatalogoArranjo.query.filter(
            db.func.lower(CatalogoArranjo.nome) == nome.lower()
        ).first()
        if existente:
            existente.usos = (existente.usos or 0) + 1
            db.session.commit()
            return existente
        novo = CatalogoArranjo(nome=nome, usos=1)
        db.session.add(novo)
        db.session.commit()
        return novo
