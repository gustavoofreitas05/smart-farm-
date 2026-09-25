"""Testes do módulo de Cultivos."""
from conftest import register_and_login


def test_create_crop_defaults_to_active(client):
    register_and_login(client)
    response = client.post(
        "/crops/create",
        data={"name": "Banana", "status": "ativo"},
        follow_redirects=True,
    )
    assert "Banana" in response.get_data(as_text=True)

    dashboard = client.get("/")
    assert "Banana" in dashboard.get_data(as_text=True)


def test_create_crop_rejects_invalid_status(client):
    register_and_login(client)
    response = client.post(
        "/crops/create",
        data={"name": "Banana", "status": "status-invalido"},
        follow_redirects=True,
    )
    assert "Status inválido" in response.get_data(as_text=True)


def test_harvested_crop_not_in_active_dashboard_list(client):
    register_and_login(client)
    client.post("/crops/create", data={"name": "Milho", "status": "ativo"})
    client.post("/crops/1/edit", data={"name": "Milho", "status": "colhido"})
    dashboard = client.get("/")
    assert "Cultivos ativos" in dashboard.get_data(as_text=True)
    # A tabela de cultivos ativos não deve listar o milho já colhido
    assert "Nenhum cultivo ativo" in dashboard.get_data(as_text=True)


def test_delete_crop(client):
    register_and_login(client)
    client.post("/crops/create", data={"name": "Banana", "status": "ativo"})
    response = client.post("/crops/1/delete", follow_redirects=True)
    assert "Nenhum cultivo cadastrado" in response.get_data(as_text=True)
