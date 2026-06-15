# -*- coding: utf-8 -*-
"""
Testes do catálogo curado de arranjos (CAT-01).

- promover insere / incrementa usos (entrada livre não polui sem confirmação);
- sugerir por substring (fallback SQLite) e ordenado por usos;
- endpoints GET /api/catalogo/arranjos e POST /api/catalogo/arranjos/promover.
"""
import os

os.environ.setdefault("BCRYPT_LOG_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-catalogo")

from app.models.catalogo_arranjo import CatalogoArranjo  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import generate_token, hash_password  # noqa: E402


def _admin(session):
    u = User(name="Admin", email="cat_admin@t.com", password_hash=hash_password("x"), role="admin")
    session.add(u)
    session.commit()
    return u


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestCatalogoModel:
    def test_promover_insere_e_incrementa(self, session):
        a = CatalogoArranjo.promover("Buquê de rosas")
        assert a.usos == 1
        a2 = CatalogoArranjo.promover("buquê de rosas")  # case-insensitive → mesma linha
        assert a2.id == a.id
        assert a2.usos == 2
        assert CatalogoArranjo.query.count() == 1

    def test_promover_vazio_nao_cria(self, session):
        assert CatalogoArranjo.promover("   ") is None
        assert CatalogoArranjo.query.count() == 0

    def test_sugerir_substring_e_ordena_por_usos(self, session):
        CatalogoArranjo.promover("Buquê de rosas")
        CatalogoArranjo.promover("Buquê de rosas")  # usos=2
        CatalogoArranjo.promover("Arranjo de girassóis")
        CatalogoArranjo.promover("Cesta de rosas brancas")

        nomes = CatalogoArranjo.sugerir("rosas")
        assert "Buquê de rosas" in nomes
        assert "Cesta de rosas brancas" in nomes
        # Mais usado primeiro
        assert nomes.index("Buquê de rosas") == 0

    def test_sugerir_sem_termo_retorna_mais_usados(self, session):
        CatalogoArranjo.promover("A")
        CatalogoArranjo.promover("B")
        CatalogoArranjo.promover("B")
        nomes = CatalogoArranjo.sugerir("")
        assert nomes[0] == "B"


class TestCatalogoEndpoints:
    def test_get_sugere(self, client, session):
        CatalogoArranjo.promover("Buquê de rosas")
        token = generate_token(_admin(session))
        resp = client.get("/api/catalogo/arranjos?q=rosas", headers=_auth(token))
        assert resp.status_code == 200
        assert "Buquê de rosas" in resp.get_json()["arranjos"]

    def test_post_promove(self, client, session):
        token = generate_token(_admin(session))
        resp = client.post(
            "/api/catalogo/arranjos/promover",
            json={"nome": "Mini suculentas"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["arranjo"]["nome"] == "Mini suculentas"
        assert CatalogoArranjo.query.filter_by(nome="Mini suculentas").count() == 1

    def test_post_sem_nome_400(self, client, session):
        token = generate_token(_admin(session))
        resp = client.post(
            "/api/catalogo/arranjos/promover", json={"nome": ""}, headers=_auth(token)
        )
        assert resp.status_code == 400
