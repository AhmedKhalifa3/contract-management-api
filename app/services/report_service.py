import pandas as pd

from app.extensions import db
from app.models import Contract
from app.services import status_service

_CONTRACT_COLUMNS = [
    "id",
    "title",
    "counterparty",
    "value",
    "category",
    "status",
    "start_date",
    "end_date",
]


def _to_dataframe(contracts: list[Contract]) -> pd.DataFrame:
    records = [
        {
            "id": c.id,
            "title": c.title,
            "counterparty": c.counterparty,
            "value": float(c.value),
            "category": c.category,
            "status": c.status.value,
            "start_date": c.start_date,
            "end_date": c.end_date,
        }
        for c in contracts
    ]
    return pd.DataFrame.from_records(records, columns=_CONTRACT_COLUMNS)


def value_by_category() -> pd.DataFrame:
    contracts = db.session.query(Contract).all()
    df = _to_dataframe(contracts)
    if df.empty:
        return pd.DataFrame(columns=["category", "contract_count", "total_value"])

    return (
        df.groupby("category")
        .agg(contract_count=("id", "count"), total_value=("value", "sum"))
        .reset_index()
        .sort_values("total_value", ascending=False)
        .reset_index(drop=True)
    )


def expiring_soon_summary(threshold_days: int = 30) -> pd.DataFrame:
    # Reuses the same "expiring soon" definition the /expiring-soon endpoint
    # and sweep job use, so the report never disagrees with the API about
    # which contracts qualify.
    contracts = status_service.list_expiring_soon(threshold_days)
    df = _to_dataframe(contracts)
    if df.empty:
        return pd.DataFrame(
            columns=["category", "contract_count", "total_value", "nearest_end_date"]
        )

    return (
        df.groupby("category")
        .agg(
            contract_count=("id", "count"),
            total_value=("value", "sum"),
            nearest_end_date=("end_date", "min"),
        )
        .reset_index()
        .sort_values("nearest_end_date")
        .reset_index(drop=True)
    )
