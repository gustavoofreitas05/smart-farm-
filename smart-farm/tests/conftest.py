"""Configuração compartilhada dos testes: cria um banco SQLite isolado por
teste (em um diretório temporário) e desliga a exigência de CSRF, já que o
test_client não navega por páginas reais para obter o token."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

import app as smart_farm


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("helpers.DATABASE", str(db_path))
    smart_farm.app.config["TESTING"] = True
    smart_farm.app.config["WTF_CSRF_ENABLED"] = False
    smart_farm.init_db(smart_farm.app)  # recria as tabelas no banco de teste
    with smart_farm.app.test_client() as client:
        yield client


def register_and_login(client, username="maria", password="senha1234"):
    client.post(
        "/register",
        data={"username": username, "password": password, "confirmation": password},
    )
    return client.post(
        "/login", data={"username": username, "password": password}, follow_redirects=True
    )
