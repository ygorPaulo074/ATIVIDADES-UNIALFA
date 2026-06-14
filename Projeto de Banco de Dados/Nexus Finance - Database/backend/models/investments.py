from pydantic import BaseModel


class InvestmentIn(BaseModel):
    symbol: str
    type: str  # stock | reit | etf | bdr | crypto | treasury | fixed_income
    purchase_date: str
    quantity: float = 0
    currency: str = "BRL"
    track_brapi: bool = False
    maturity_date: str | None = None
    notes: str | None = None


class InvestmentUpdate(BaseModel):
    symbol: str | None = None
    quantity: float | None = None
    notes: str | None = None
    track_brapi: bool | None = None
    maturity_date: str | None = None


class ContributionIn(BaseModel):
    type: str  # deposit | withdrawal
    amount: float
    date: str
    notes: str | None = None


class QuoteIn(BaseModel):
    date: str
    price: float
