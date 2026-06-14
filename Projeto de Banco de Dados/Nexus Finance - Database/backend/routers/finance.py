from fastapi import APIRouter, Depends, Query

from deps import current_user, guard
from models.finance import (
    BillIn,
    BillUpdate,
    CategoryIn,
    CategoryUpdate,
    InstallmentPlanIn,
    MaterializeIn,
    PayBillIn,
    RecurrenceIn,
    TagIn,
    TransactionIn,
    TransactionUpdate,
    WalletIn,
    WalletUpdate,
)
from services import finance_service as svc

router = APIRouter(tags=["finance"])


# ---- Wallets ----
@router.get("/wallets")
def list_wallets(u=Depends(current_user)):
    return svc.list_wallets(u["id"])


@router.post("/wallets")
def create_wallet(data: WalletIn, u=Depends(current_user)):
    return guard(lambda: svc.create_wallet(u["id"], data.model_dump()))


@router.patch("/wallets/{wid}")
def update_wallet(wid: int, data: WalletUpdate, u=Depends(current_user)):
    return guard(lambda: svc.update_wallet(u["id"], wid, data.model_dump()))


@router.delete("/wallets/{wid}")
def delete_wallet(wid: int, u=Depends(current_user)):
    svc.delete_wallet(u["id"], wid)
    return {"ok": True}


# ---- Categories ----
@router.get("/categories")
def list_categories(u=Depends(current_user)):
    return svc.list_categories(u["id"])


@router.post("/categories")
def create_category(data: CategoryIn, u=Depends(current_user)):
    return guard(lambda: svc.create_category(u["id"], data.model_dump()))


@router.patch("/categories/{cid}")
def update_category(cid: int, data: CategoryUpdate, u=Depends(current_user)):
    return guard(lambda: svc.update_category(u["id"], cid, data.model_dump()))


@router.delete("/categories/{cid}")
def delete_category(cid: int, u=Depends(current_user)):
    return guard(lambda: (svc.delete_category(u["id"], cid), {"ok": True})[1])


# ---- Tags ----
@router.get("/tags")
def list_tags(u=Depends(current_user)):
    return svc.list_tags(u["id"])


@router.post("/tags")
def create_tag(data: TagIn, u=Depends(current_user)):
    return guard(lambda: svc.create_tag(u["id"], data.model_dump()))


@router.delete("/tags/{tid}")
def delete_tag(tid: int, u=Depends(current_user)):
    svc.delete_tag(u["id"], tid)
    return {"ok": True}


# ---- Payment methods ----
@router.get("/payment-methods")
def list_payment_methods(u=Depends(current_user)):
    return svc.list_payment_methods()


# ---- Bills ----
@router.get("/bills")
def list_bills(u=Depends(current_user)):
    return svc.list_bills(u["id"])


@router.post("/bills")
def create_bill(data: BillIn, u=Depends(current_user)):
    return guard(lambda: svc.create_bill(u["id"], data.model_dump()))


@router.patch("/bills/{bid}")
def update_bill(bid: int, data: BillUpdate, u=Depends(current_user)):
    return guard(lambda: svc.update_bill(u["id"], bid, data.model_dump()))


@router.post("/bills/{bid}/pay")
def pay_bill(bid: int, data: PayBillIn, u=Depends(current_user)):
    return guard(lambda: svc.pay_bill(u["id"], bid, data.model_dump()))


@router.post("/bills/{bid}/cancel")
def cancel_bill(bid: int, u=Depends(current_user)):
    svc.cancel_bill(u["id"], bid)
    return {"ok": True}


@router.delete("/bills/{bid}")
def delete_bill(bid: int, u=Depends(current_user)):
    svc.delete_bill(u["id"], bid)
    return {"ok": True}


# ---- Transactions ----
@router.get("/transactions")
def list_transactions(u=Depends(current_user)):
    return svc.list_transactions(u["id"])


@router.post("/transactions")
def create_transaction(data: TransactionIn, u=Depends(current_user)):
    return guard(lambda: svc.create_transaction(u["id"], data.model_dump()))


@router.patch("/transactions/{tid}")
def update_transaction(tid: int, data: TransactionUpdate, u=Depends(current_user)):
    return guard(lambda: svc.update_transaction(u["id"], tid, data.model_dump()))


@router.delete("/transactions/{tid}")
def delete_transaction(tid: int, u=Depends(current_user)):
    svc.delete_transaction(u["id"], tid)
    return {"ok": True}


# ---- Recurrences ----
@router.get("/recurrences")
def list_recurrences(u=Depends(current_user)):
    return svc.list_recurrences(u["id"])


@router.post("/recurrences")
def create_recurrence(data: RecurrenceIn, u=Depends(current_user)):
    return guard(lambda: svc.create_recurrence(u["id"], data.model_dump()))


@router.post("/recurrences/{rid}/materialize")
def materialize_recurrence(rid: int, data: MaterializeIn, u=Depends(current_user)):
    return guard(lambda: svc.materialize_recurrence(u["id"], rid, data.until))


@router.post("/recurrences/{rid}/toggle")
def toggle_recurrence(rid: int, u=Depends(current_user)):
    return guard(lambda: svc.toggle_recurrence(u["id"], rid))


@router.delete("/recurrences/{rid}")
def delete_recurrence(rid: int, u=Depends(current_user)):
    svc.delete_recurrence(u["id"], rid)
    return {"ok": True}


# ---- Installment plans ----
@router.get("/installment-plans")
def list_installment_plans(u=Depends(current_user)):
    return svc.list_installment_plans(u["id"])


@router.post("/installment-plans")
def create_installment_plan(data: InstallmentPlanIn, u=Depends(current_user)):
    return guard(lambda: svc.create_installment_plan(u["id"], data.model_dump()))


@router.delete("/installment-plans/{pid}")
def delete_installment_plan(pid: int, u=Depends(current_user)):
    svc.delete_installment_plan(u["id"], pid)
    return {"ok": True}


# ---- Cash flow ----
@router.get("/cash-flow")
def cash_flow(
    start: str = Query(...), end: str = Query(...),
    granularity: str = Query("monthly"), u=Depends(current_user),
):
    return svc.cash_flow(u["id"], start, end, granularity)
