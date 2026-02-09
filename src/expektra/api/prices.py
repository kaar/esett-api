from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from expektra.db import get_session
from expektra.models import ImbalancePrice
from expektra.schemas import ImbalancePriceDataPoint, PaginatedResponse
from expektra.sync.esett_client import MBA_EIC_CODES

_prices_table: Table = ImbalancePrice.__table__  # type: ignore[assignment]

router = APIRouter()


def parse_prices_row(mba: str, row: dict[str, object]) -> dict[str, object]:
    """Convert an eSett JSON row to a dict matching the ImbalancePrice model."""
    ts_str = row.get("timestampUTC")
    if not isinstance(ts_str, str):
        raise ValueError(f"Missing timestampUTC in row: {row}")

    return {
        "time": datetime.fromisoformat(ts_str.replace("Z", "+00:00")),
        "mba": mba,
        "up_reg_price": row.get("upRegPrice"),
        "down_reg_price": row.get("downRegPrice"),
        "imbl_purchase_price": row.get("imblPurchasePrice"),
        "imbl_sales_price": row.get("imblSalesPrice"),
        "imbl_spot_difference_price": row.get("imblSpotDifferencePrice"),
        "incentivising_component": row.get("incentivisingComponent"),
        "main_dir_reg_power_per_mba": row.get("mainDirRegPowerPerMBA"),
        "value_of_avoided_activation": row.get("valueOfAvoidedActivation"),
        "up_reg_price_frr_a": row.get("upRegPriceFrrA"),
        "down_reg_price_frr_a": row.get("downRegPriceFrrA"),
    }


async def upsert_prices(session: AsyncSession, rows: list[dict[str, object]]) -> int:
    """Insert imbalance price rows using ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    stmt = pg_insert(_prices_table).values(rows).on_conflict_do_nothing()
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def is_range_cached(
    session: AsyncSession, mba: str, start: datetime, end: datetime
) -> bool:
    """Check if the DB has sufficient data for the given range."""
    expected = (end - start).total_seconds() / 3600  # hourly intervals
    if expected <= 0:
        return False

    query = (
        select(func.count())
        .select_from(_prices_table)
        .where(
            ImbalancePrice.mba == mba,
            ImbalancePrice.time >= start,
            ImbalancePrice.time < end,
        )
    )
    result = await session.execute(query)
    actual = result.scalar_one()
    return actual >= expected * 0.9


@router.get("/api/prices")
async def get_prices(
    request: Request,
    mba: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[ImbalancePriceDataPoint]:
    if mba not in MBA_EIC_CODES:
        raise HTTPException(status_code=400, detail=f"Unknown MBA: {mba}")

    cached = await is_range_cached(session, mba, start, end)

    if not cached:
        esett_client = request.app.state.esett_client
        raw = await esett_client.fetch_prices(mba, start, end)
        if raw:
            parsed = [parse_prices_row(mba, r) for r in raw]
            await upsert_prices(session, parsed)

    query = (
        select(ImbalancePrice)
        .where(
            ImbalancePrice.mba == mba,
            ImbalancePrice.time >= start,
            ImbalancePrice.time < end,
        )
        .order_by(ImbalancePrice.time)
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rows = result.scalars().all()

    data = [
        ImbalancePriceDataPoint(
            time=r.time,
            mba=r.mba,
            up_reg_price=r.up_reg_price,
            down_reg_price=r.down_reg_price,
            imbl_purchase_price=r.imbl_purchase_price,
            imbl_sales_price=r.imbl_sales_price,
            imbl_spot_difference_price=r.imbl_spot_difference_price,
            incentivising_component=r.incentivising_component,
            main_dir_reg_power_per_mba=r.main_dir_reg_power_per_mba,
            value_of_avoided_activation=r.value_of_avoided_activation,
            up_reg_price_frr_a=r.up_reg_price_frr_a,
            down_reg_price_frr_a=r.down_reg_price_frr_a,
        )
        for r in rows
    ]

    return PaginatedResponse[ImbalancePriceDataPoint](
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        cached=cached,
    )
