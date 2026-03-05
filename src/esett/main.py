from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from esett.api.consumption import router as consumption_router
from esett.api.load_profile import router as load_profile_router
from esett.api.prices import router as prices_router
from esett.api.production import router as production_router
from esett.db import engine
from esett.models import Base
from esett.sync.esett_client import EsettClient

_HYPERTABLES = ["load_profile", "production", "consumption", "imbalance_price"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    db_engine = getattr(app.state, "engine", engine)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table in _HYPERTABLES:
            await conn.execute(
                text(
                    f"SELECT create_hypertable('{table}', 'time', "
                    f"chunk_time_interval => INTERVAL '7 days', "
                    f"if_not_exists => TRUE, migrate_data => TRUE)"
                )
            )
    app.state.esett_client = EsettClient()
    yield
    await app.state.esett_client.close()


app = FastAPI(
    title="eSett API",
    description="API proxy for eSett Open Data. Caches responses in TimescaleDB.",
    version=version("esett"),
    lifespan=lifespan,
)

app.include_router(load_profile_router)
app.include_router(production_router)
app.include_router(consumption_router)
app.include_router(prices_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
