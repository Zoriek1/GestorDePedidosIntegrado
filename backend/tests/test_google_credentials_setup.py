# -*- coding: utf-8 -*-
"""
Testes para _setup_google_credentials (factory.py)

Verifica que as credenciais Google são escritas a partir da variável de ambiente
GOOGLE_CREDENTIALS_JSON quando o arquivo ainda não existe no container/VPS.
"""
import json
import types

import pytest


def make_app(root_path: str):
    """Cria um mock mínimo de Flask app para os testes."""
    return types.SimpleNamespace(root_path=root_path)


def test_cria_arquivo_a_partir_de_env(tmp_path, monkeypatch):
    """Se GOOGLE_CREDENTIALS_JSON está definida e o arquivo não existe, cria-o."""
    creds_data = {"type": "service_account", "project_id": "test-project"}
    creds_path = tmp_path / "google_credentials.json"

    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", json.dumps(creds_data))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    _setup_google_credentials(make_app(str(tmp_path)))

    assert creds_path.exists(), "Arquivo de credenciais deve ter sido criado"
    written = json.loads(creds_path.read_text(encoding="utf-8"))
    assert written["type"] == "service_account"
    assert written["project_id"] == "test-project"


def test_nao_sobrescreve_arquivo_existente(tmp_path, monkeypatch):
    """Não sobrescreve o arquivo se ele já existe."""
    creds_path = tmp_path / "google_credentials.json"
    original = {"type": "service_account", "project_id": "original"}
    creds_path.write_text(json.dumps(original), encoding="utf-8")

    new_creds = {"type": "service_account", "project_id": "should-not-appear"}
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", json.dumps(new_creds))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    _setup_google_credentials(make_app(str(tmp_path)))

    written = json.loads(creds_path.read_text(encoding="utf-8"))
    assert written["project_id"] == "original", "Arquivo existente não deve ser sobrescrito"


def test_noop_quando_env_nao_definida(tmp_path, monkeypatch):
    """Não cria nenhum arquivo quando GOOGLE_CREDENTIALS_JSON não está definida."""
    monkeypatch.delenv("GOOGLE_CREDENTIALS_JSON", raising=False)
    creds_path = tmp_path / "google_credentials.json"
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    _setup_google_credentials(make_app(str(tmp_path)))

    assert not creds_path.exists(), "Nenhum arquivo deve ser criado sem a env var"


def test_noop_quando_env_vazia(tmp_path, monkeypatch):
    """Não cria arquivo quando GOOGLE_CREDENTIALS_JSON é string vazia."""
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", "   ")
    creds_path = tmp_path / "google_credentials.json"
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    _setup_google_credentials(make_app(str(tmp_path)))

    assert not creds_path.exists(), "Nenhum arquivo deve ser criado com env var vazia"


def test_nao_levanta_excecao_com_json_invalido(tmp_path, monkeypatch, capsys):
    """Lida graciosamente com JSON inválido — não lança exceção."""
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", "isso-nao-e-json-valido")
    creds_path = tmp_path / "google_credentials.json"
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    # Não deve levantar nenhuma exceção
    _setup_google_credentials(make_app(str(tmp_path)))

    assert not creds_path.exists(), "Arquivo não deve ser criado com JSON inválido"

    captured = capsys.readouterr()
    assert "AVISO" in captured.out or "Falha" in captured.out, (
        "Deve imprimir aviso sobre JSON inválido"
    )


def test_cria_diretorios_pai_se_necessario(tmp_path, monkeypatch):
    """Cria os diretórios pai quando eles não existem."""
    creds_path = tmp_path / "user" / "config" / "google_credentials.json"
    assert not creds_path.parent.exists(), "Diretório pai não deve existir antes do teste"

    creds_data = {"type": "service_account", "project_id": "nested-test"}
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", json.dumps(creds_data))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    _setup_google_credentials(make_app(str(tmp_path)))

    assert creds_path.exists(), "Arquivo deve ser criado mesmo com diretórios pai faltando"
    written = json.loads(creds_path.read_text(encoding="utf-8"))
    assert written["project_id"] == "nested-test"


def test_imprime_confirmacao_ao_criar_arquivo(tmp_path, monkeypatch, capsys):
    """Imprime mensagem de confirmação quando cria o arquivo com sucesso."""
    creds_data = {"type": "service_account", "project_id": "test"}
    creds_path = tmp_path / "google_credentials.json"

    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", json.dumps(creds_data))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_path))

    from app.factory import _setup_google_credentials

    _setup_google_credentials(make_app(str(tmp_path)))

    captured = capsys.readouterr()
    assert "GOOGLE" in captured.out or "google_credentials" in captured.out, (
        "Deve imprimir confirmação de criação"
    )
