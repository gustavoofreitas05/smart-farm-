import os
from datetime import date, datetime, timedelta

from flask import (Flask, abort, flash, redirect, render_template, request,
                    session, url_for)
from flask_session import Session
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import (ValidationError, brl, get_db, get_owned_or_404, init_db,
                      login_required, optional_text, parse_date, parse_int,
                      parse_number, required_text)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_TYPE"] = "filesystem"
# Cookies de sessão mais seguros: não acessíveis via JS e não enviados em
# navegação cross-site (mitiga roubo de sessão via XSS/CSRF).
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
Session(app)

# Proteção CSRF: toda rota POST/PUT/DELETE exige um token válido, gerado por
# csrf_token() nos templates e verificado automaticamente pelo Flask-WTF.
csrf = CSRFProtect(app)

app.jinja_env.filters["brl"] = brl

init_db(app)

EXPENSE_CATEGORIES = [
    "Ração", "Medicamentos", "Manutenção", "Ferramentas",
    "Animais", "Plantio", "Energia", "Outros",
]
CROP_STATUSES = ["ativo", "colhido", "perdido"]
PT_MONTHS = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# ---------------------------------------------------------------------------
# Páginas de erro
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def handle_404(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def handle_500(e):
    return render_template("errors/500.html"), 500


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Sua sessão expirou ou o formulário é inválido. Tente novamente.", "error")
    return redirect(request.referrer or url_for("index"))


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        try:
            if not username or len(username) < 3:
                raise ValidationError("O usuário deve ter pelo menos 3 caracteres.")
            if not password or len(password) < 8:
                raise ValidationError("A senha precisa ter pelo menos 8 caracteres.")
            if password != confirmation:
                raise ValidationError("As senhas não coincidem.")

            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                raise ValidationError("Esse nome de usuário já está em uso.")

            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
            flash("Conta criada! Agora faça login.", "success")
            return redirect(url_for("login"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        # Mensagem genérica de propósito: não revela se o problema foi o
        # usuário ou a senha, para não ajudar quem está tentando adivinhar.
        if user is None or not check_password_hash(user["hash"], password):
            flash("Usuário ou senha inválidos.", "error")
            return render_template("login.html")

        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def month_bounds(ref_date, months_back=0):
    """Retorna (início, próximo_início) do mês `months_back` meses antes de ref_date."""
    y, m = ref_date.year, ref_date.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    start = date(y, m, 1)
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return start, date(ny, nm, 1)


@app.route("/")
@login_required
def index():
    db = get_db()
    user_id = session["user_id"]
    today = date.today()

    total_animals = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM animals WHERE user_id = ?",
        (user_id,),
    ).fetchone()["total"]

    active_crops = db.execute(
        "SELECT * FROM crops WHERE user_id = ? AND status = 'ativo' ORDER BY planting_date DESC",
        (user_id,),
    ).fetchall()

    low_stock = db.execute(
        """SELECT * FROM inventory
           WHERE user_id = ? AND quantity <= minimum_quantity
           ORDER BY (quantity - minimum_quantity) ASC""",
        (user_id,),
    ).fetchall()

    # --- Produção nos últimos 7 dias (KPI + gráfico diário) ---------------
    week_ago = (today - timedelta(days=6)).isoformat()
    production_week = db.execute(
        """SELECT COALESCE(SUM(quantity), 0) AS total FROM production
           WHERE user_id = ? AND production_date >= ?""",
        (user_id, week_ago),
    ).fetchone()["total"]

    production_rows = db.execute(
        """SELECT production_date, SUM(quantity) AS total FROM production
           WHERE user_id = ? AND production_date >= ?
           GROUP BY production_date""",
        (user_id, week_ago),
    ).fetchall()
    totals_by_day = {row["production_date"]: row["total"] for row in production_rows}
    chart_labels, chart_values = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        chart_labels.append(day.strftime("%d/%m"))
        chart_values.append(totals_by_day.get(day.isoformat(), 0))

    # --- Produção por tipo nos últimos 30 dias (o que a fazenda mais produz) -
    month_ago = (today - timedelta(days=29)).isoformat()
    production_by_type = db.execute(
        """SELECT type, SUM(quantity) AS total FROM production
           WHERE user_id = ? AND production_date >= ?
           GROUP BY type ORDER BY total DESC LIMIT 8""",
        (user_id, month_ago),
    ).fetchall()

    # --- Gastos do mês + comparação com o mês anterior (indicador) -------
    month_start, next_month_start = month_bounds(today, 0)
    prev_month_start, _ = month_bounds(today, 1)

    expenses_month = db.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
           WHERE user_id = ? AND expense_date >= ? AND expense_date < ?""",
        (user_id, month_start.isoformat(), next_month_start.isoformat()),
    ).fetchone()["total"]

    expenses_prev_month = db.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
           WHERE user_id = ? AND expense_date >= ? AND expense_date < ?""",
        (user_id, prev_month_start.isoformat(), month_start.isoformat()),
    ).fetchone()["total"]

    if expenses_prev_month > 0:
        expenses_change_pct = round(
            ((expenses_month - expenses_prev_month) / expenses_prev_month) * 100, 1
        )
    else:
        expenses_change_pct = None

    expenses_by_category = db.execute(
        """SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses
           WHERE user_id = ? AND expense_date >= ? AND expense_date < ?
           GROUP BY category ORDER BY total DESC""",
        (user_id, month_start.isoformat(), next_month_start.isoformat()),
    ).fetchall()

    # --- Histórico de gastos nos últimos 6 meses (tendência) --------------
    months = []
    cursor_start = month_start
    for i in range(5, -1, -1):
        s, _ = month_bounds(today, i)
        months.append(s)
    six_months_ago = months[0].isoformat()

    expense_rows = db.execute(
        "SELECT expense_date, amount FROM expenses WHERE user_id = ? AND expense_date >= ?",
        (user_id, six_months_ago),
    ).fetchall()
    totals_by_month = {m.strftime("%Y-%m"): 0.0 for m in months}
    for row in expense_rows:
        key = row["expense_date"][:7]
        if key in totals_by_month:
            totals_by_month[key] += row["amount"]

    expense_trend_labels = [f"{PT_MONTHS[m.month]}/{str(m.year)[2:]}" for m in months]
    expense_trend_values = [round(totals_by_month[m.strftime("%Y-%m")], 2) for m in months]

    return render_template(
        "index.html",
        total_animals=total_animals,
        active_crops=active_crops,
        production_week=production_week,
        expenses_month=expenses_month,
        expenses_change_pct=expenses_change_pct,
        low_stock=low_stock,
        expenses_by_category=expenses_by_category,
        chart_labels=chart_labels,
        chart_values=chart_values,
        production_by_type=production_by_type,
        expense_trend_labels=expense_trend_labels,
        expense_trend_values=expense_trend_values,
    )


# ---------------------------------------------------------------------------
# Animais
# ---------------------------------------------------------------------------

@app.route("/animals")
@login_required
def animals_index():
    db = get_db()
    animals = db.execute(
        "SELECT * FROM animals WHERE user_id = ? ORDER BY name",
        (session["user_id"],),
    ).fetchall()
    return render_template("animals/index.html", animals=animals)


@app.route("/animals/create", methods=["GET", "POST"])
@login_required
def animals_create():
    if request.method == "POST":
        try:
            name = required_text(request.form.get("name"), "Nome")
            species = required_text(request.form.get("species"), "Espécie")
            breed = optional_text(request.form.get("breed"))
            sex = request.form.get("sex", "")
            birth_date = parse_date(request.form.get("birth_date"), "Data de nascimento",
                                     allow_future=False, required=False)
            quantity = parse_int(request.form.get("quantity", "1"), "Quantidade", minimum=1)
            notes = optional_text(request.form.get("notes"))

            db = get_db()
            db.execute(
                """INSERT INTO animals (user_id, name, species, breed, sex, birth_date, quantity, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], name, species, breed, sex, birth_date, quantity, notes),
            )
            db.commit()
            flash("Animal cadastrado com sucesso.", "success")
            return redirect(url_for("animals_index"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("animals/create.html", form=request.form)

    return render_template("animals/create.html", form={})


@app.route("/animals/<int:animal_id>/edit", methods=["GET", "POST"])
@login_required
def animals_edit(animal_id):
    db = get_db()
    animal = get_owned_or_404("animals", animal_id, session["user_id"], db)
    if animal is None:
        abort(404)

    if request.method == "POST":
        try:
            name = required_text(request.form.get("name"), "Nome")
            species = required_text(request.form.get("species"), "Espécie")
            breed = optional_text(request.form.get("breed"))
            sex = request.form.get("sex", "")
            birth_date = parse_date(request.form.get("birth_date"), "Data de nascimento",
                                     allow_future=False, required=False)
            quantity = parse_int(request.form.get("quantity", "1"), "Quantidade", minimum=1)
            notes = optional_text(request.form.get("notes"))

            db.execute(
                """UPDATE animals SET name=?, species=?, breed=?, sex=?, birth_date=?,
                   quantity=?, notes=? WHERE id=? AND user_id=?""",
                (name, species, breed, sex, birth_date, quantity, notes,
                 animal_id, session["user_id"]),
            )
            db.commit()
            flash("Animal atualizado.", "success")
            return redirect(url_for("animals_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("animals/edit.html", animal=animal)


@app.route("/animals/<int:animal_id>/delete", methods=["POST"])
@login_required
def animals_delete(animal_id):
    db = get_db()
    if get_owned_or_404("animals", animal_id, session["user_id"], db) is None:
        abort(404)
    db.execute(
        "DELETE FROM animals WHERE id = ? AND user_id = ?",
        (animal_id, session["user_id"]),
    )
    db.commit()
    flash("Animal removido.", "success")
    return redirect(url_for("animals_index"))


# ---------------------------------------------------------------------------
# Produção
# ---------------------------------------------------------------------------

@app.route("/production")
@login_required
def production_index():
    db = get_db()
    records = db.execute(
        """SELECT production.*, animals.name AS animal_name FROM production
           LEFT JOIN animals ON animals.id = production.animal_id
           WHERE production.user_id = ?
           ORDER BY production_date DESC, production.id DESC""",
        (session["user_id"],),
    ).fetchall()
    return render_template("production/index.html", records=records)


def _production_form(db, user_id):
    return db.execute(
        "SELECT * FROM animals WHERE user_id = ? ORDER BY name", (user_id,)
    ).fetchall()


@app.route("/production/create", methods=["GET", "POST"])
@login_required
def production_create():
    db = get_db()
    animals = _production_form(db, session["user_id"])

    if request.method == "POST":
        try:
            animal_id = request.form.get("animal_id") or None
            type_ = required_text(request.form.get("type"), "Tipo")
            quantity = parse_number(request.form.get("quantity"), "Quantidade", allow_zero=False)
            unit = required_text(request.form.get("unit"), "Unidade", max_length=30)
            production_date = parse_date(
                request.form.get("production_date") or date.today().isoformat(),
                "Data", allow_future=False,
            )
            notes = optional_text(request.form.get("notes"))

            if animal_id and get_owned_or_404("animals", int(animal_id), session["user_id"], db) is None:
                raise ValidationError("Animal selecionado é inválido.")

            db.execute(
                """INSERT INTO production (user_id, animal_id, type, quantity, unit, production_date, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], animal_id, type_, quantity, unit, production_date, notes),
            )
            db.commit()
            flash("Produção registrada.", "success")
            return redirect(url_for("production_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("production/create.html", animals=animals)


@app.route("/production/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def production_edit(record_id):
    db = get_db()
    record = get_owned_or_404("production", record_id, session["user_id"], db)
    if record is None:
        abort(404)
    animals = _production_form(db, session["user_id"])

    if request.method == "POST":
        try:
            animal_id = request.form.get("animal_id") or None
            type_ = required_text(request.form.get("type"), "Tipo")
            quantity = parse_number(request.form.get("quantity"), "Quantidade", allow_zero=False)
            unit = required_text(request.form.get("unit"), "Unidade", max_length=30)
            production_date = parse_date(request.form.get("production_date"), "Data", allow_future=False)
            notes = optional_text(request.form.get("notes"))

            if animal_id and get_owned_or_404("animals", int(animal_id), session["user_id"], db) is None:
                raise ValidationError("Animal selecionado é inválido.")

            db.execute(
                """UPDATE production SET animal_id=?, type=?, quantity=?, unit=?,
                   production_date=?, notes=? WHERE id=? AND user_id=?""",
                (animal_id, type_, quantity, unit, production_date, notes,
                 record_id, session["user_id"]),
            )
            db.commit()
            flash("Registro de produção atualizado.", "success")
            return redirect(url_for("production_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("production/edit.html", record=record, animals=animals)


@app.route("/production/<int:record_id>/delete", methods=["POST"])
@login_required
def production_delete(record_id):
    db = get_db()
    if get_owned_or_404("production", record_id, session["user_id"], db) is None:
        abort(404)
    db.execute(
        "DELETE FROM production WHERE id = ? AND user_id = ?",
        (record_id, session["user_id"]),
    )
    db.commit()
    flash("Registro de produção removido.", "success")
    return redirect(url_for("production_index"))


# ---------------------------------------------------------------------------
# Despesas
# ---------------------------------------------------------------------------

@app.route("/expenses")
@login_required
def expenses_index():
    db = get_db()
    records = db.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY expense_date DESC, id DESC",
        (session["user_id"],),
    ).fetchall()
    total = sum(r["amount"] for r in records)
    return render_template("expenses/index.html", records=records, total=total)


@app.route("/expenses/create", methods=["GET", "POST"])
@login_required
def expenses_create():
    if request.method == "POST":
        try:
            category = required_text(request.form.get("category"), "Categoria")
            if category not in EXPENSE_CATEGORIES:
                raise ValidationError("Categoria inválida.")
            description = optional_text(request.form.get("description"))
            amount = parse_number(request.form.get("amount"), "Valor", allow_zero=False)
            expense_date = parse_date(
                request.form.get("expense_date") or date.today().isoformat(),
                "Data", allow_future=False,
            )
            notes = optional_text(request.form.get("notes"))

            db = get_db()
            db.execute(
                """INSERT INTO expenses (user_id, category, description, amount, expense_date, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session["user_id"], category, description, amount, expense_date, notes),
            )
            db.commit()
            flash("Despesa registrada.", "success")
            return redirect(url_for("expenses_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("expenses/create.html", categories=EXPENSE_CATEGORIES)


@app.route("/expenses/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def expenses_edit(record_id):
    db = get_db()
    record = get_owned_or_404("expenses", record_id, session["user_id"], db)
    if record is None:
        abort(404)

    if request.method == "POST":
        try:
            category = required_text(request.form.get("category"), "Categoria")
            if category not in EXPENSE_CATEGORIES:
                raise ValidationError("Categoria inválida.")
            description = optional_text(request.form.get("description"))
            amount = parse_number(request.form.get("amount"), "Valor", allow_zero=False)
            expense_date = parse_date(request.form.get("expense_date"), "Data", allow_future=False)
            notes = optional_text(request.form.get("notes"))

            db.execute(
                """UPDATE expenses SET category=?, description=?, amount=?, expense_date=?, notes=?
                   WHERE id=? AND user_id=?""",
                (category, description, amount, expense_date, notes, record_id, session["user_id"]),
            )
            db.commit()
            flash("Despesa atualizada.", "success")
            return redirect(url_for("expenses_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("expenses/edit.html", record=record, categories=EXPENSE_CATEGORIES)


@app.route("/expenses/<int:record_id>/delete", methods=["POST"])
@login_required
def expenses_delete(record_id):
    db = get_db()
    if get_owned_or_404("expenses", record_id, session["user_id"], db) is None:
        abort(404)
    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (record_id, session["user_id"]),
    )
    db.commit()
    flash("Despesa removida.", "success")
    return redirect(url_for("expenses_index"))


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------

@app.route("/inventory")
@login_required
def inventory_index():
    db = get_db()
    items = db.execute(
        "SELECT * FROM inventory WHERE user_id = ? ORDER BY name",
        (session["user_id"],),
    ).fetchall()
    return render_template("inventory/index.html", items=items)


@app.route("/inventory/create", methods=["GET", "POST"])
@login_required
def inventory_create():
    if request.method == "POST":
        try:
            name = required_text(request.form.get("name"), "Nome")
            category = optional_text(request.form.get("category"), max_length=100)
            quantity = parse_number(request.form.get("quantity"), "Quantidade")
            unit = required_text(request.form.get("unit"), "Unidade", max_length=30)
            minimum_quantity = parse_number(request.form.get("minimum_quantity"), "Quantidade mínima")

            db = get_db()
            db.execute(
                """INSERT INTO inventory (user_id, name, category, quantity, unit, minimum_quantity, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], name, category, quantity, unit, minimum_quantity,
                 datetime.now().isoformat(timespec="seconds")),
            )
            db.commit()
            flash("Item de estoque cadastrado.", "success")
            return redirect(url_for("inventory_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("inventory/create.html")


@app.route("/inventory/<int:item_id>/update", methods=["POST"])
@login_required
def inventory_update(item_id):
    db = get_db()
    if get_owned_or_404("inventory", item_id, session["user_id"], db) is None:
        abort(404)
    try:
        quantity = parse_number(request.form.get("quantity"), "Quantidade")
        db.execute(
            "UPDATE inventory SET quantity = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (quantity, datetime.now().isoformat(timespec="seconds"), item_id, session["user_id"]),
        )
        db.commit()
        flash("Estoque atualizado.", "success")
    except ValidationError as e:
        flash(str(e), "error")
    return redirect(url_for("inventory_index"))


@app.route("/inventory/<int:item_id>/delete", methods=["POST"])
@login_required
def inventory_delete(item_id):
    db = get_db()
    if get_owned_or_404("inventory", item_id, session["user_id"], db) is None:
        abort(404)
    db.execute(
        "DELETE FROM inventory WHERE id = ? AND user_id = ?",
        (item_id, session["user_id"]),
    )
    db.commit()
    flash("Item de estoque removido.", "success")
    return redirect(url_for("inventory_index"))


# ---------------------------------------------------------------------------
# Cultivos
# ---------------------------------------------------------------------------

@app.route("/crops")
@login_required
def crops_index():
    db = get_db()
    crops = db.execute(
        "SELECT * FROM crops WHERE user_id = ? ORDER BY status, planting_date DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("crops/index.html", crops=crops)


@app.route("/crops/create", methods=["GET", "POST"])
@login_required
def crops_create():
    if request.method == "POST":
        try:
            name = required_text(request.form.get("name"), "Nome do cultivo")
            area = optional_text(request.form.get("area"), max_length=100)
            planting_date = parse_date(request.form.get("planting_date"), "Data de plantio",
                                        allow_future=False, required=False)
            expected_harvest = parse_date(request.form.get("expected_harvest"), "Previsão de colheita",
                                           required=False)
            status = request.form.get("status", "ativo")
            if status not in CROP_STATUSES:
                raise ValidationError("Status inválido.")
            notes = optional_text(request.form.get("notes"))

            db = get_db()
            db.execute(
                """INSERT INTO crops (user_id, name, area, planting_date, expected_harvest, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], name, area, planting_date, expected_harvest, status, notes),
            )
            db.commit()
            flash("Cultivo cadastrado.", "success")
            return redirect(url_for("crops_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("crops/create.html", statuses=CROP_STATUSES)


@app.route("/crops/<int:crop_id>/edit", methods=["GET", "POST"])
@login_required
def crops_edit(crop_id):
    db = get_db()
    crop = get_owned_or_404("crops", crop_id, session["user_id"], db)
    if crop is None:
        abort(404)

    if request.method == "POST":
        try:
            name = required_text(request.form.get("name"), "Nome do cultivo")
            area = optional_text(request.form.get("area"), max_length=100)
            planting_date = parse_date(request.form.get("planting_date"), "Data de plantio",
                                        allow_future=False, required=False)
            expected_harvest = parse_date(request.form.get("expected_harvest"), "Previsão de colheita",
                                           required=False)
            status = request.form.get("status", "ativo")
            if status not in CROP_STATUSES:
                raise ValidationError("Status inválido.")
            notes = optional_text(request.form.get("notes"))

            db.execute(
                """UPDATE crops SET name=?, area=?, planting_date=?, expected_harvest=?,
                   status=?, notes=? WHERE id=? AND user_id=?""",
                (name, area, planting_date, expected_harvest, status, notes,
                 crop_id, session["user_id"]),
            )
            db.commit()
            flash("Cultivo atualizado.", "success")
            return redirect(url_for("crops_index"))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("crops/edit.html", crop=crop, statuses=CROP_STATUSES)


@app.route("/crops/<int:crop_id>/delete", methods=["POST"])
@login_required
def crops_delete(crop_id):
    db = get_db()
    if get_owned_or_404("crops", crop_id, session["user_id"], db) is None:
        abort(404)
    db.execute(
        "DELETE FROM crops WHERE id = ? AND user_id = ?",
        (crop_id, session["user_id"]),
    )
    db.commit()
    flash("Cultivo removido.", "success")
    return redirect(url_for("crops_index"))


if __name__ == "__main__":
    app.run(debug=True)
