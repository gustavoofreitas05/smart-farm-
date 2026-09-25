import sqlite3
from datetime import date
from functools import wraps

from flask import g, redirect, session, url_for

DATABASE = "database/smart_farm.db"


def get_db():
    """Abre (ou reaproveita) a conexão SQLite da requisição atual."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Cria as tabelas a partir de database/schema.sql, se ainda não existirem.

    Pode ser chamada mais de uma vez (ex.: para recriar o banco em testes),
    mas só registra o teardown_appcontext na primeira vez.
    """
    with app.app_context():
        db = get_db()
        with app.open_resource("database/schema.sql") as f:
            db.executescript(f.read().decode("utf8"))
        db.commit()
        close_db()  # fecha esta conexão de setup para não vazar entre bancos diferentes

    if not app.config.get("_SMART_FARM_TEARDOWN_REGISTERED"):
        app.teardown_appcontext(close_db)
        app.config["_SMART_FARM_TEARDOWN_REGISTERED"] = True


def login_required(f):
    """Redireciona para /login se o usuário não estiver autenticado."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def brl(value):
    """Formata um número como moeda brasileira: 1234.5 -> R$ 1.234,50"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    text = f"{value:,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


# ---------------------------------------------------------------------------
# Validação de formulários
# ---------------------------------------------------------------------------
# Todas as rotas que recebem dados de formulário usam estas funções em vez de
# converter valores "na mão", para nunca deixar um erro de digitação do
# usuário virar um erro 500 (Internal Server Error) sem explicação.

class ValidationError(Exception):
    """Erro de validação de formulário, com mensagem amigável para o usuário."""


def required_text(value, field_label, max_length=200):
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field_label} é obrigatório.")
    if len(value) > max_length:
        raise ValidationError(f"{field_label} deve ter no máximo {max_length} caracteres.")
    return value


def optional_text(value, max_length=500):
    value = (value or "").strip()
    if len(value) > max_length:
        raise ValidationError(f"Texto muito longo (máximo {max_length} caracteres).")
    return value


def parse_number(value, field_label, *, minimum=0, allow_zero=True):
    """Converte texto em float, aceitando tanto vírgula quanto ponto decimal."""
    if value is None or str(value).strip() == "":
        raise ValidationError(f"{field_label} é obrigatório.")
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError:
        raise ValidationError(f"{field_label} deve ser um número válido.")
    if number < minimum:
        raise ValidationError(f"{field_label} não pode ser menor que {minimum}.")
    if not allow_zero and number == 0:
        raise ValidationError(f"{field_label} deve ser maior que zero.")
    return number


def parse_int(value, field_label, *, minimum=1):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field_label} deve ser um número inteiro.")
    if number < minimum:
        raise ValidationError(f"{field_label} deve ser pelo menos {minimum}.")
    return number


def parse_date(value, field_label, *, allow_future=True, required=True):
    """Valida uma data no formato ISO (yyyy-mm-dd) vinda de um <input type=date>."""
    value = (value or "").strip()
    if not value:
        if required:
            raise ValidationError(f"{field_label} é obrigatória.")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValidationError(f"{field_label} inválida.")
    if not allow_future and parsed > date.today():
        raise ValidationError(f"{field_label} não pode ser no futuro.")
    return parsed.isoformat()


def get_owned_or_404(table, record_id, user_id, db):
    """Busca um registro garantindo que ele pertence ao usuário logado.

    Retorna None se o registro não existir OU pertencer a outro usuário —
    de propósito, para não revelar se o id existe na base de outra conta.
    """
    return db.execute(
        f"SELECT * FROM {table} WHERE id = ? AND user_id = ?",
        (record_id, user_id),
    ).fetchone()
