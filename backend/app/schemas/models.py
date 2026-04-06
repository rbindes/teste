import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


# --- Auth ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    household_id: uuid.UUID | None = None  # None = criar novo household


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    household_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Account ---
class AccountCreate(BaseModel):
    bank_name: str
    type: str  # CHECKING, SAVINGS, CREDIT_CARD
    name: str  # apelido: "Nubank CC - Maria"
    owner_id: uuid.UUID
    last_four_digits: str | None = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    bank_name: str
    type: str
    name: str
    owner_id: uuid.UUID
    last_four_digits: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Transaction ---
class TransactionPreview(BaseModel):
    date: date
    description: str
    amount: float
    type: str  # EXPENSE ou INCOME


class TransactionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    date: date
    description: str
    amount: float
    type: str
    category_id: int | None
    category_name: str | None = None
    is_manual_category: bool
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionCategoryUpdate(BaseModel):
    category_id: int
    create_rule: bool = False  # criar regra automática para esse padrão


class TransactionCreate(BaseModel):
    account_id: uuid.UUID
    date: date
    description: str
    amount: float
    type: str
    category_id: int | None = None


# --- Upload ---
class UploadPreviewResponse(BaseModel):
    upload_id: uuid.UUID
    filename: str
    file_type: str
    transactions: list[TransactionPreview]
    total_count: int


class UploadConfirmResponse(BaseModel):
    upload_id: uuid.UUID
    transactions_imported: int
    transactions_skipped: int


class UploadHistoryResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    transactions_imported: int
    transactions_skipped: int
    created_at: datetime
    account_name: str | None = None

    model_config = {"from_attributes": True}


# --- Category ---
class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: str
    color: str

    model_config = {"from_attributes": True}


class CategoryRuleCreate(BaseModel):
    pattern: str
    category_id: int
    priority: int = 0


class CategoryRuleResponse(BaseModel):
    id: int
    pattern: str
    category_id: int
    category_name: str | None = None
    priority: int

    model_config = {"from_attributes": True}


# --- Dashboard ---
class DRELineItem(BaseModel):
    category: str
    amount: float
    percentage: float


class DREResponse(BaseModel):
    period: str
    total_income: float
    income_items: list[DRELineItem]
    total_expenses: float
    expense_items: list[DRELineItem]
    balance: float
    savings_rate: float


class MonthlyDataPoint(BaseModel):
    month: str
    income: float
    expenses: float
    balance: float


class PersonComparisonItem(BaseModel):
    category: str
    person_a_amount: float
    person_b_amount: float


class TopExpenseItem(BaseModel):
    date: date
    description: str
    amount: float
    category: str | None
    account_name: str


# --- Insights ---
class InsightItem(BaseModel):
    type: str  # ALERT, OPPORTUNITY, GOAL, COMPARISON
    title: str
    description: str
    icon: str
