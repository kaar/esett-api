from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from expektra.db import get_session
from expektra.models import LoadProfile
from expektra.schemas import LoadProfileDataPoint, PaginatedResponse
from expektra.sync.esett_client import MBA_EIC_CODES

_load_profile_table: Table = LoadProfile.__table__  # type: ignore[assignment]

router = APIRouter()


def parse_load_profile_row(mba: str, row: dict[str, object]) -> dict[str, object]:
    """Convert an eSett JSON row to a dict matching the LoadProfile model.

    Handles the mga_code null -> "" sentinel mapping.
    """
    ts_str = row.get("timestampUTC")
    if not isinstance(ts_str, str):
        raise ValueError(f"Missing timestampUTC in row: {row}")

    return {
        "time": datetime.fromisoformat(ts_str.replace("Z", "+00:00")),
        "mba": mba,
        "mga_code": row.get("mgaCode") or "",
        "mga_name": row.get("mgaName"),
        "quantity": row.get("quantity"),
    }


async def upsert_load_profiles(
    session: AsyncSession, rows: list[dict[str, object]]
) -> int:
    """Insert load profile rows using ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    stmt = pg_insert(_load_profile_table).values(rows).on_conflict_do_nothing()
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def is_range_cached(
    session: AsyncSession,
    mba: str,
    start: datetime,
    end: datetime,
    mga_code: str | None = None,
) -> bool:
    """Check if the DB has sufficient data for the given range."""
    expected = (end - start).total_seconds() / 900  # 15-min intervals
    if expected <= 0:
        return False

    query = (
        select(func.count())
        .select_from(_load_profile_table)
        .where(
            LoadProfile.mba == mba,
            LoadProfile.time >= start,
            LoadProfile.time < end,
        )
    )
    if mga_code is not None:
        query = query.where(LoadProfile.mga_code == mga_code)
    else:
        query = query.where(LoadProfile.mga_code == "")

    result = await session.execute(query)
    actual = result.scalar_one()
    return actual >= expected * 0.9


@router.get("/api/load-profile")
async def get_load_profile(
    request: Request,
    mba: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    mga: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[LoadProfileDataPoint]:
    if mba not in MBA_EIC_CODES:
        raise HTTPException(status_code=400, detail=f"Unknown MBA: {mba}")

    mga_sentinel = mga if mga is not None else ""
    cached = await is_range_cached(session, mba, start, end, mga_sentinel)

    if not cached:
        esett_client = request.app.state.esett_client
        raw = await esett_client.fetch_load_profile(mba, start, end, mga=mga)
        if raw:
            parsed = [parse_load_profile_row(mba, r) for r in raw]
            await upsert_load_profiles(session, parsed)

    # Query from DB
    query = (
        select(LoadProfile)
        .where(
            LoadProfile.mba == mba,
            LoadProfile.time >= start,
            LoadProfile.time < end,
        )
        .order_by(LoadProfile.time)
    )
    if mga is not None:
        query = query.where(LoadProfile.mga_code == mga)
    else:
        query = query.where(LoadProfile.mga_code == "")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rows = result.scalars().all()

    data = [
        LoadProfileDataPoint(
            time=r.time,
            mba=r.mba,
            mga_code=r.mga_code or None,
            mga_name=r.mga_name,
            quantity=r.quantity,
        )
        for r in rows
    ]

    return PaginatedResponse[LoadProfileDataPoint](
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        cached=cached,
    )
