from pydantic import BaseModel


class WalletIn(BaseModel):
    name: str
    initial_balance: float = 0


class WalletUpdate(BaseModel):
    name: str | None = None
    initial_balance: float | None = None


class CategoryIn(BaseModel):
    name: str
    type: str  # income | expense


class CategoryUpdate(BaseModel):
    name: str | None = None
    type: str | None = None


class TagIn(BaseModel):
    name: str


class BillIn(BaseModel):
    type: str  # payable | receivable
    description: str
    amount: float
    due_date: str
    counterparty: str | None = None
    category_id: int | None = None
    payment_method_id: int | None = None


class BillUpdate(BaseModel):
    description: str | None = None
    amount: float | None = None
    due_date: str | None = None
    counterparty: str | None = None
    category_id: int | None = None
    payment_method_id: int | None = None


class PayBillIn(BaseModel):
    wallet_id: int
    amount: float
    date: str | None = None


class TransactionIn(BaseModel):
    wallet_id: int
    type: str  # inflow | outflow
    description: str
    amount: float
    date: str
    category_id: int | None = None
    payment_method_id: int | None = None
    notes: str | None = None


class TransactionUpdate(BaseModel):
    description: str | None = None
    amount: float | None = None
    date: str | None = None
    category_id: int | None = None
    payment_method_id: int | None = None
    notes: str | None = None


class RecurrenceIn(BaseModel):
    type: str
    description: str
    amount: float
    frequency: str  # weekly | monthly | yearly
    reference_day: int
    start_date: str
    interval_count: int = 1
    category_id: int | None = None
    payment_method_id: int | None = None
    end_date: str | None = None
    occurrences_count: int | None = None
    materialize: bool = True


class MaterializeIn(BaseModel):
    until: str


class InstallmentPlanIn(BaseModel):
    description: str
    total_amount: float
    total_installments: int
    purchase_date: str
    category_id: int | None = None
    payment_method_id: int | None = None
