"""Testes do módulo de Produção."""
from conftest import register_and_login


def test_create_production(client):
    register_and_login(client)
    response = client.post(
        "/production/create",
        data={"type": "Leite", "quantity": "5", "unit": "litros", "production_date": "2026-09-20"},
        follow_redirects=True,
    )
    assert "Leite" in response.get_data(as_text=True)


def test_create_production_rejects_zero_quantity(client):
    register_and_login(client)
    response = client.post(
        "/production/create",
        data={"type": "Leite", "quantity": "0", "unit": "litros", "production_date": "2026-09-20"},
        follow_redirects=True,
    )
    assert "maior que zero" in response.get_data(as_text=True)


def test_create_production_rejects_future_date(client):
    register_and_login(client)
    response = client.post(
        "/production/create",
        data={"type": "Leite", "quantity": "5", "unit": "litros", "production_date": "2099-01-01"},
        follow_redirects=True,
    )
    assert "não pode ser no futuro" in response.get_data(as_text=True)


def test_production_linked_to_animal(client):
    register_and_login(client)
    client.post("/animals/create", data={"name": "Mimosa", "species": "Vaca", "quantity": "1"})
    response = client.post(
        "/production/create",
        data={
            "type": "Leite", "quantity": "5", "unit": "litros",
            "production_date": "2026-09-20", "animal_id": "1",
        },
        follow_redirects=True,
    )
    assert "Mimosa" in response.get_data(as_text=True)


def test_edit_and_delete_production(client):
    register_and_login(client)
    client.post(
        "/production/create",
        data={"type": "Leite", "quantity": "5", "unit": "litros", "production_date": "2026-09-20"},
    )
    response = client.post(
        "/production/1/edit",
        data={"type": "Ovos", "quantity": "12", "unit": "unidades", "production_date": "2026-09-21"},
        follow_redirects=True,
    )
    assert "Ovos" in response.get_data(as_text=True)

    response = client.post("/production/1/delete", follow_redirects=True)
    assert "Ovos" not in response.get_data(as_text=True)
