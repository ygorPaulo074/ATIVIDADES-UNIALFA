from datetime import date

from services import brapi_service
from services import db_service as db

_ALLOWED_INVEST_PATCH = {"symbol", "quantity", "notes", "track_brapi", "maturity_date"}


def _owns(uid: int, iid: int) -> bool:
    return db.query_one("SELECT 1 FROM investments WHERE id = %s AND user_id = %s", (iid, uid)) is not None


def list_investments(uid):
    """Lista com métricas derivadas (investido, valor da posição, retorno)."""
    return db.query_all(
        "SELECT i.*, invested_total(i.id) AS invested, position_value(i.id) AS position, "
        "investment_return(i.id) AS return_value "
        "FROM investments i WHERE user_id = %s ORDER BY id", (uid,))


def create_investment(uid, d):
    return db.query_one(
        "INSERT INTO investments(user_id, symbol, type, quantity, currency, track_brapi, purchase_date, maturity_date, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (uid, d["symbol"], d["type"], d["quantity"], d.get("currency", "BRL"),
         d.get("track_brapi", False), d["purchase_date"], d.get("maturity_date"), d.get("notes")))


def update_investment(uid, iid, d):
    if not _owns(uid, iid):
        raise PermissionError("investment")
    fields = {k: v for k, v in d.items() if v is not None and k in _ALLOWED_INVEST_PATCH}
    if not fields:
        return db.query_one("SELECT * FROM investments WHERE id = %s", (iid,))
    sets = ", ".join(f"{k} = %s" for k in fields)
    vals = list(fields.values()) + [iid, uid]
    return db.query_one(
        f"UPDATE investments SET {sets} WHERE id = %s AND user_id = %s RETURNING *", vals)


def delete_investment(uid, iid):
    db.execute("DELETE FROM investments WHERE id = %s AND user_id = %s", (iid, uid))


def list_contributions(uid, iid):
    if not _owns(uid, iid):
        raise PermissionError("investment")
    return db.query_all(
        "SELECT id, type, amount, date, notes FROM contributions WHERE investment_id = %s ORDER BY date DESC", (iid,))


def add_contribution(uid, iid, d):
    if not _owns(uid, iid):
        raise PermissionError("investment")
    return db.query_one(
        "INSERT INTO contributions(investment_id, type, amount, date, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (iid, d["type"], d["amount"], d["date"], d.get("notes")))


def list_history(uid, iid):
    if not _owns(uid, iid):
        raise PermissionError("investment")
    return db.query_all(
        "SELECT date, market_value FROM value_history WHERE investment_id = %s ORDER BY date", (iid,))


def record_quote(uid, iid, quote_date, price):
    """Registra/atualiza o preço unitário de um dia (entrada manual)."""
    if not _owns(uid, iid):
        raise PermissionError("investment")
    db.execute("SELECT record_market_value(%s, %s::date, %s::numeric)", (iid, quote_date, price))


def sync_brapi(uid):
    """Sincroniza os preços do dia (brapi) dos investimentos com track_brapi=true."""
    invs = db.query_all(
        "SELECT id, symbol FROM investments WHERE user_id = %s AND track_brapi = true", (uid,))
    symbols = sorted({i["symbol"] for i in invs})
    prices = brapi_service.fetch_quotes(symbols)

    today = date.today()
    updated = 0
    for i in invs:
        price = prices.get(i["symbol"])
        if price is not None:
            db.execute("SELECT record_market_value(%s, %s::date, %s::numeric)", (i["id"], today, price))
            updated += 1
    return {"updated": updated, "symbols": symbols, "prices": prices}
