"""Pydantic request/response schemas for the Portfolio API (api-spec §8-§10).

Money fields accept Decimal on input and are serialized as numeric strings on
output (api-spec §5.3 decimal-safe representation).
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

# api-spec §5.3: money leaves the API as strings, never as JSON floats.
Money = Annotated[Decimal | None, Field(default=None)]


def serialize_money(value: Decimal | float | None) -> str | None:
    """Deterministic decimal string; None stays None (api-spec §4.3: no zero placeholder).

    Trailing zeros are stripped so "584.000000000000" serializes as "584".
    """
    if value is None:
        return None
    return format(Decimal(str(value)).normalize(), "f")


class PortfolioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    # api-spec §8.2 contract name; stored as reporting_currency (schema-spec §5.1).
    base_currency: str = Field(min_length=3, max_length=10, pattern=r"^[A-Z]{3,5}$")


class PortfolioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(ACTIVE|ARCHIVED)$")
    # base_currency is intentionally not updatable: financial history must not
    # change reporting currency silently (schema-spec §15.3).


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: str = Field(min_length=1)
    asset_id: str | None = None
    transaction_type: str = Field(pattern=r"^(BUY|SELL|DEPOSIT|WITHDRAWAL|FEE|DIVIDEND|INTEREST)$")
    quantity: Money
    price: Money
    # api-spec §9.2 contract name `fee`; stored as fee_amount (schema-spec §5.2).
    fee: Money
    currency: str | None = Field(default=None, min_length=3, max_length=10, pattern=r"^[A-Z]{3,5}$")
    executed_at: datetime | None = None
    gross_amount: Money
    notes: str | None = None
