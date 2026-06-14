from urllib.error import URLError

from fastapi import APIRouter, Depends, HTTPException

from deps import current_user, guard
from models.investments import ContributionIn, InvestmentIn, InvestmentUpdate, QuoteIn
from services import investments_service as svc

router = APIRouter(tags=["investments"])


@router.get("/investments")
def list_investments(u=Depends(current_user)):
    return svc.list_investments(u["id"])


@router.post("/investments")
def create_investment(data: InvestmentIn, u=Depends(current_user)):
    return guard(lambda: svc.create_investment(u["id"], data.model_dump()))


@router.patch("/investments/{iid}")
def update_investment(iid: int, data: InvestmentUpdate, u=Depends(current_user)):
    return guard(lambda: svc.update_investment(u["id"], iid, data.model_dump()))


@router.delete("/investments/{iid}")
def delete_investment(iid: int, u=Depends(current_user)):
    svc.delete_investment(u["id"], iid)
    return {"ok": True}


@router.post("/investments/{iid}/contributions")
def add_contribution(iid: int, data: ContributionIn, u=Depends(current_user)):
    return guard(lambda: svc.add_contribution(u["id"], iid, data.model_dump()))


@router.get("/investments/{iid}/contributions")
def list_contributions(iid: int, u=Depends(current_user)):
    return guard(lambda: svc.list_contributions(u["id"], iid))


@router.get("/investments/{iid}/history")
def list_history(iid: int, u=Depends(current_user)):
    return guard(lambda: svc.list_history(u["id"], iid))


@router.post("/investments/{iid}/quote")
def record_quote(iid: int, data: QuoteIn, u=Depends(current_user)):
    return guard(lambda: (svc.record_quote(u["id"], iid, data.date, data.price), {"ok": True})[1])


@router.post("/investments/sync-brapi")
def sync_brapi(u=Depends(current_user)):
    try:
        return svc.sync_brapi(u["id"])
    except URLError:
        raise HTTPException(status_code=502, detail="Não foi possível contatar a brapi.dev")
