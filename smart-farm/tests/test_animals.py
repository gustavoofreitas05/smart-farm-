"""Testes do fluxo de autenticação e do módulo de Animais."""
from conftest import register_and_login


def test_register_and_login(client):
    response = register_and_login(client)
    assert response.status_code == 200
    assert "Dashboard" in response.get_data(as_text=True)


def test_register_rejects_short_password(client):
    response = client.post(
        "/register",
        data={"username": "joao", "password": "123", "confirmation": "123"},
        follow_redirects=True,
    )
    assert "pelo menos 8 caracteres" in response.get_data(as_text=True)


def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        "/register",
        data={"username": "joao", "password": "senha1234", "confirmation": "outra1234"},
        follow_redirects=True,
    )
    assert "não coincidem" in response.get_data(as_text=True)


def test_login_wrong_password(client):
    register_and_login(client, "joao", "senha1234")
    client.get("/logout")
    response = client.post(
        "/login", data={"username": "joao", "password": "errada123"}, follow_redirects=True
    )
    assert "inválidos" in response.get_data(as_text=True)


def test_dashboard_requires_login(client):
    response = client.get("/", follow_redirects=True)
    assert "Entrar" in response.get_data(as_text=True)


def test_create_animal(client):
    register_and_login(client)
    response = client.post(
        "/animals/create",
        data={"name": "Mimosa", "species": "Vaca", "quantity": "1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Mimosa" in response.get_data(as_text=True)


def test_create_animal_requires_species(client):
    register_and_login(client)
    response = client.post(
        "/animals/create",
        data={"name": "Mimosa", "species": "", "quantity": "1"},
        follow_redirects=True,
    )
    assert "obrigatório" in response.get_data(as_text=True)


def test_create_animal_rejects_invalid_quantity(client):
    register_and_login(client)
    response = client.post(
        "/animals/create",
        data={"name": "Mimosa", "species": "Vaca", "quantity": "abc"},
        follow_redirects=True,
    )
    assert "número inteiro" in response.get_data(as_text=True)


def test_edit_animal(client):
    register_and_login(client)
    client.post("/animals/create", data={"name": "Mimosa", "species": "Vaca", "quantity": "1"})
    response = client.post(
        "/animals/1/edit",
        data={"name": "Estrela", "species": "Vaca", "quantity": "2"},
        follow_redirects=True,
    )
    assert "Estrela" in response.get_data(as_text=True)


def test_delete_animal(client):
    register_and_login(client)
    client.post("/animals/create", data={"name": "Mimosa", "species": "Vaca", "quantity": "1"})
    response = client.post("/animals/1/delete", follow_redirects=True)
    assert "Mimosa" not in response.get_data(as_text=True)


def test_user_cannot_edit_others_animal(client, tmp_path, monkeypatch):
    register_and_login(client, "ana", "senha1234")
    client.post("/animals/create", data={"name": "VacaDaAna", "species": "Vaca", "quantity": "1"})
    client.get("/logout")

    register_and_login(client, "bruno", "senha1234")
    response = client.get("/animals/1/edit")
    assert response.status_code == 404
