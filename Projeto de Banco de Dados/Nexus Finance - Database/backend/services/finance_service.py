from services import db_service as db

# Todas as operações são escopadas pelo usuário (user_id) e chamam, quando há
# lógica, as funções SQL do banco (sem ORM).

_ALLOWED_PATCH = {
    "wallets":      {"name", "initial_balance"},
    "categories":   {"name", "type"},
    "bills":        {"description", "amount", "due_date", "counterparty", "category_id", "payment_method_id"},
    "transactions": {"description", "amount", "date", "category_id", "payment_method_id", "notes"},
    "investments":  {"symbol", "quantity", "notes", "track_brapi", "maturity_date"},
}


def _owns(uid: int, table: str, _id: int) -> bool:
    # `table` é literal interno (nunca entrada do usuário)
    return db.query_one(f"SELECT 1 FROM {table} WHERE id = %s AND user_id = %s", (_id, uid)) is not None


def _patch(uid: int, table: str, _id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None and k in _ALLOWED_PATCH[table]}
    if not fields:
        return db.query_one(f"SELECT * FROM {table} WHERE id = %s AND user_id = %s", (_id, uid))
    sets = ", ".join(f"{k} = %s" for k in fields)
    vals = list(fields.values()) + [_id, uid]
    return db.query_one(
        f"UPDATE {table} SET {sets} WHERE id = %s AND user_id = %s RETURNING *", vals)


# ---- Wallets ----

def list_wallets(uid):
    return db.query_all(
        "SELECT id, name, initial_balance, wallet_balance(id) AS balance "
        "FROM wallets WHERE user_id = %s ORDER BY id", (uid,))


def create_wallet(uid, d):
    return db.query_one(
        "INSERT INTO wallets(user_id, name, initial_balance) VALUES (%s, %s, %s) "
        "RETURNING id, name, initial_balance",
        (uid, d["name"], d["initial_balance"]))


def update_wallet(uid, wid, d):
    return _patch(uid, "wallets", wid, d)


def delete_wallet(uid, wid):
    db.execute("DELETE FROM wallets WHERE id = %s AND user_id = %s", (wid, uid))


# ---- Categories ----

def list_categories(uid):
    return db.query_all("SELECT id, name, type FROM categories WHERE user_id = %s ORDER BY type, name", (uid,))


def create_category(uid, d):
    return db.query_one(
        "INSERT INTO categories(user_id, name, type) VALUES (%s, %s, %s) RETURNING id, name, type",
        (uid, d["name"], d["type"]))


def update_category(uid, cid, d):
    return _patch(uid, "categories", cid, d)


def delete_category(uid, cid):
    db.execute("DELETE FROM categories WHERE id = %s AND user_id = %s", (cid, uid))


# ---- Tags (máx. 5 por usuário — trigger no banco) ----

def list_tags(uid):
    return db.query_all("SELECT id, name FROM tags WHERE user_id = %s ORDER BY name", (uid,))


def create_tag(uid, d):
    return db.query_one("INSERT INTO tags(user_id, name) VALUES (%s, %s) RETURNING id, name", (uid, d["name"]))


def delete_tag(uid, tid):
    db.execute("DELETE FROM tags WHERE id = %s AND user_id = %s", (tid, uid))


# ---- Payment methods (lista fixa global) ----

def list_payment_methods():
    return db.query_all("SELECT id, name FROM payment_methods ORDER BY id")


# ---- Bills (contas a pagar/receber) ----

def list_bills(uid):
    return db.query_all(
        "SELECT b.*, bill_status(b.id) AS status FROM bills b WHERE user_id = %s ORDER BY due_date", (uid,))


def create_bill(uid, d):
    return db.query_one(
        "INSERT INTO bills(user_id, type, description, amount, due_date, counterparty, category_id, payment_method_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (uid, d["type"], d["description"], d["amount"], d["due_date"],
         d.get("counterparty"), d.get("category_id"), d.get("payment_method_id")))


def update_bill(uid, bid, d):
    return _patch(uid, "bills", bid, d)


def cancel_bill(uid, bid):
    db.execute("UPDATE bills SET cancelled_at = now() WHERE id = %s AND user_id = %s", (bid, uid))


def delete_bill(uid, bid):
    db.execute("DELETE FROM bills WHERE id = %s AND user_id = %s", (bid, uid))


def pay_bill(uid, bid, d):
    if not _owns(uid, "bills", bid):
        raise PermissionError("bill")
    if not _owns(uid, "wallets", d["wallet_id"]):
        raise PermissionError("wallet")
    return db.query_one(
        "SELECT pay_bill(%s, %s, %s::numeric, COALESCE(%s::date, CURRENT_DATE)) AS tx_id",
        (bid, d["wallet_id"], d["amount"], d.get("date")))


# ---- Transactions ----

def list_transactions(uid):
    return db.query_all("SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC, id DESC", (uid,))


def create_transaction(uid, d):
    if not _owns(uid, "wallets", d["wallet_id"]):
        raise PermissionError("wallet")
    return db.query_one(
        "INSERT INTO transactions(user_id, wallet_id, type, description, amount, date, category_id, payment_method_id, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (uid, d["wallet_id"], d["type"], d["description"], d["amount"], d["date"],
         d.get("category_id"), d.get("payment_method_id"), d.get("notes")))


def update_transaction(uid, tid, d):
    return _patch(uid, "transactions", tid, d)


def delete_transaction(uid, tid):
    db.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (tid, uid))


# ---- Recurrences ----

def list_recurrences(uid):
    return db.query_all("SELECT * FROM recurrences WHERE user_id = %s ORDER BY id", (uid,))


def create_recurrence(uid, d):
    return db.query_one(
        "INSERT INTO recurrences(user_id, type, description, amount, category_id, payment_method_id, "
        "frequency, interval_count, reference_day, start_date, end_date, occurrences_count, materialize) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (uid, d["type"], d["description"], d["amount"], d.get("category_id"), d.get("payment_method_id"),
         d["frequency"], d.get("interval_count", 1), d["reference_day"], d["start_date"],
         d.get("end_date"), d.get("occurrences_count"), d.get("materialize", True)))


def materialize_recurrence(uid, rid, until):
    if not _owns(uid, "recurrences", rid):
        raise PermissionError("recurrence")
    return db.query_one("SELECT generate_recurrence_occurrences(%s, %s) AS created", (rid, until))


def toggle_recurrence(uid, rid):
    return db.query_one(
        "UPDATE recurrences SET active = NOT active WHERE id = %s AND user_id = %s RETURNING id, active",
        (rid, uid))


def delete_recurrence(uid, rid):
    db.execute("DELETE FROM recurrences WHERE id = %s AND user_id = %s", (rid, uid))


# ---- Installment plans ----

def list_installment_plans(uid):
    return db.query_all("SELECT * FROM installment_plans WHERE user_id = %s ORDER BY id", (uid,))


def create_installment_plan(uid, d):
    plan = db.query_one(
        "INSERT INTO installment_plans(user_id, description, total_amount, total_installments, "
        "category_id, payment_method_id, purchase_date) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (uid, d["description"], d["total_amount"], d["total_installments"],
         d.get("category_id"), d.get("payment_method_id"), d["purchase_date"]))
    res = db.query_one("SELECT generate_installments(%s) AS installments", (plan["id"],))
    return {"id": plan["id"], "installments": res["installments"]}


def delete_installment_plan(uid, pid):
    db.execute("DELETE FROM installment_plans WHERE id = %s AND user_id = %s", (pid, uid))


# ---- Cash flow ----

def cash_flow(uid, start, end, granularity):
    return db.query_all("SELECT * FROM cash_flow(%s, %s, %s, %s)", (uid, start, end, granularity))
