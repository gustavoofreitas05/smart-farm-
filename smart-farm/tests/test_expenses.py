"""Testes do módulo de Despesas."""
from conftest import register_and_login


def test_create_expense(client):
    register_and_login(client)
    response = client.post(
        "/expenses/create",
        data={"category": "Ração", "amount": "350", "expense_date": "2026-09-01"},
        follow_redirects=True,
    )
    assert "Ração" in response.get_data(as_text=True)


def test_create_expense_rejects_invalid_category(client):
    register_and_login(client)
    response = client.post(
        "/expenses/create",
        data={"category": "Categoria Inexistente", "amount": "100", "expense_date": "2026-09-01"},
        follow_redirects=True,
    )
    assert "Categoria inválida" in response.get_data(as_text=True)


def test_create_expense_rejects_negative_amount(client):
    register_and_login(client)
    response = client.post(
        "/expenses/create",
        data={"category": "Ração", "amount": "-50", "expense_date": "2026-09-01"},
        follow_redirects=True,
    )
    assert "não pode ser menor que" in response.get_data(as_text=True)


def test_expenses_total_is_sum_of_records(client):
    register_and_login(client)
    client.post("/expenses/create", data={"category": "Ração", "amount": "100", "expense_date": "2026-09-01"})
    client.post("/expenses/create", data={"category": "Energia", "amount": "50", "expense_date": "2026-09-02"})
    response = client.get("/expenses")
    body = response.get_data(as_text=True)
    assert "R$ 150,00" in body


def test_edit_and_delete_expense(client):
    register_and_login(client)
    client.post("/expenses/create", data={"category": "Ração", "amount": "100", "expense_date": "2026-09-01"})
    response = client.post(
        "/expenses/1/edit",
        data={"category": "Energia", "amount": "80", "expense_date": "2026-09-02"},
        follow_redirects=True,
    )
    assert "Energia" in response.get_data(as_text=True)

    response = client.post("/expenses/1/delete", follow_redirects=True)
    assert "Nenhuma despesa registrada" in response.get_data(as_text=True)
