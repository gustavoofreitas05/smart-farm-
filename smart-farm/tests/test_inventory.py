"""Testes do módulo de Estoque, incluindo o alerta de estoque baixo."""
from conftest import register_and_login


def test_create_inventory_item(client):
    register_and_login(client)
    response = client.post(
        "/inventory/create",
        data={"name": "Ração", "category": "Alimentação", "quantity": "25", "unit": "kg", "minimum_quantity": "10"},
        follow_redirects=True,
    )
    assert "Ração" in response.get_data(as_text=True)


def test_low_stock_flag_shown(client):
    register_and_login(client)
    client.post(
        "/inventory/create",
        data={"name": "Ração", "category": "Alimentação", "quantity": "5", "unit": "kg", "minimum_quantity": "10"},
    )
    response = client.get("/inventory")
    assert "Baixo" in response.get_data(as_text=True)

    dashboard = client.get("/")
    assert "Itens com estoque baixo" in dashboard.get_data(as_text=True)


def test_update_inventory_quantity(client):
    register_and_login(client)
    client.post(
        "/inventory/create",
        data={"name": "Ração", "category": "Alimentação", "quantity": "5", "unit": "kg", "minimum_quantity": "10"},
    )
    response = client.post("/inventory/1/update", data={"quantity": "20"}, follow_redirects=True)
    assert "20.0 kg" in response.get_data(as_text=True) or "20 kg" in response.get_data(as_text=True)


def test_delete_inventory_item(client):
    register_and_login(client)
    client.post(
        "/inventory/create",
        data={"name": "Ração", "category": "Alimentação", "quantity": "5", "unit": "kg", "minimum_quantity": "10"},
    )
    response = client.post("/inventory/1/delete", follow_redirects=True)
    assert "Nenhum item de estoque cadastrado" in response.get_data(as_text=True)
