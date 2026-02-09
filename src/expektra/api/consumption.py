from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from expektra.db import get_session
from expektra.models import Consumption
from expektra.schemas import ConsumptionDataPoint, PaginatedResponse
from expektra.sync.esett_client import MBA_EIC_CODES

_consumption_table: Table = Consumption.__table__  # type: ignore[assignment]

router = APIRouter()


def parse_consumption_row(mba: str, row: dict[str, object]) -> dict[str, object]:
    """Convert an eSett JSON row to a dict matching the Consumption model."""
    ts_str = row.get("timestampUTC")
    if not isinstance(ts_str, str):
        raise ValueError(f"Missing timestampUTC in row: {row}")

    return {
        "time": datetime.fromisoformat(ts_str.replace("Z", "+00:00")),
        "mba": mba,
        "total": row.get("total"),
        "metered": row.get("metered"),
        "profiled": row.get("profiled"),
        "flex": row.get("flex"),
    }


async def upsert_consumption(
    session: AsyncSession, rows: list[dict[str, object]]
) -> int:
    """Insert consumption rows using ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    stmt = pg_insert(_consumption_table).values(rows).on_conflict_do_nothing()
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
        .select_from(_consumption_table)
        .where(
            Consumption.mba == mba,
            Consumption.time >= start,
            Consumption.time < end,
        )
    )
    result = await session.execute(query)
    actual = result.scalar_one()
    return actual >= expected * 0.9


@router.get("/api/consumption")
async def get_consumption(
    request: Request,
    mba: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[ConsumptionDataPoint]:
    if mba not in MBA_EIC_CODES:
        raise HTTPException(status_code=400, detail=f"Unknown MBA: {mba}")

    cached = await is_range_cached(session, mba, start, end)

    if not cached:
        esett_client = request.app.state.esett_client
        raw = await esett_client.fetch_consumption(mba, start, end)
        if raw:
            parsed = [parse_consumption_row(mba, r) for r in raw]
            await upsert_consumption(session, parsed)

    query = (
        select(Consumption)
        .where(
            Consumption.mba == mba,
            Consumption.time >= start,
            Consumption.time < end,
        )
        .order_by(Consumption.time)
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rows = result.scalars().all()

    data = [
        ConsumptionDataPoint(
            time=r.time,
            mba=r.mba,
            total=r.total,
            metered=r.metered,
            profiled=r.profiled,
            flex=r.flex,
        )
        for r in rows
    ]

    return PaginatedResponse[ConsumptionDataPoint](
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        cached=cached,
    )
