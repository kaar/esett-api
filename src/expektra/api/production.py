from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from expektra.db import get_session
from expektra.models import Production
from expektra.schemas import PaginatedResponse, ProductionDataPoint
from expektra.sync.esett_client import MBA_EIC_CODES

_production_table: Table = Production.__table__  # type: ignore[assignment]

router = APIRouter()


def parse_production_row(mba: str, row: dict[str, object]) -> dict[str, object]:
    """Convert an eSett JSON row to a dict matching the Production model."""
    ts_str = row.get("timestampUTC")
    if not isinstance(ts_str, str):
        raise ValueError(f"Missing timestampUTC in row: {row}")

    return {
        "time": datetime.fromisoformat(ts_str.replace("Z", "+00:00")),
        "mba": mba,
        "total": row.get("total"),
        "hydro": row.get("hydro"),
        "wind": row.get("wind"),
        "wind_offshore": row.get("windOffshore"),
        "solar": row.get("solar"),
        "nuclear": row.get("nuclear"),
        "thermal": row.get("thermal"),
        "energy_storage": row.get("energyStorage"),
        "other": row.get("other"),
    }


async def upsert_production(
    session: AsyncSession, rows: list[dict[str, object]]
) -> int:
    """Insert production rows using ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    stmt = pg_insert(_production_table).values(rows).on_conflict_do_nothing()
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
        .select_from(_production_table)
        .where(
            Production.mba == mba,
            Production.time >= start,
            Production.time < end,
        )
    )
    result = await session.execute(query)
    actual = result.scalar_one()
    return actual >= expected * 0.9


@router.get("/api/production")
async def get_production(
    request: Request,
    mba: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[ProductionDataPoint]:
    if mba not in MBA_EIC_CODES:
        raise HTTPException(status_code=400, detail=f"Unknown MBA: {mba}")

    cached = await is_range_cached(session, mba, start, end)

    if not cached:
        esett_client = request.app.state.esett_client
        raw = await esett_client.fetch_production(mba, start, end)
        if raw:
            parsed = [parse_production_row(mba, r) for r in raw]
            await upsert_production(session, parsed)

    query = (
        select(Production)
        .where(
            Production.mba == mba,
            Production.time >= start,
            Production.time < end,
        )
        .order_by(Production.time)
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rows = result.scalars().all()

    data = [
        ProductionDataPoint(
            time=r.time,
            mba=r.mba,
            total=r.total,
            hydro=r.hydro,
            wind=r.wind,
            wind_offshore=r.wind_offshore,
            solar=r.solar,
            nuclear=r.nuclear,
            thermal=r.thermal,
            energy_storage=r.energy_storage,
            other=r.other,
        )
        for r in rows
    ]

    return PaginatedResponse[ProductionDataPoint](
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        cached=cached,
    )
