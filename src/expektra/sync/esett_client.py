from datetime import datetime

import httpx

ESETT_BASE_URL = "https://api.opendata.esett.com"

MBA_EIC_CODES: dict[str, str] = {
    "SE1": "10Y1001A1001A44P",
    "SE2": "10Y1001A1001A45N",
    "SE3": "10Y1001A1001A46L",
    "SE4": "10Y1001A1001A47J",
    "FI": "10YFI-1--------U",
    "NO1": "10YNO-1--------2",
    "NO2": "10YNO-2--------T",
    "NO3": "10YNO-3--------J",
    "NO4": "10YNO-4--------9",
    "NO5": "10Y1001A1001A48H",
    "DK1": "10YDK-1--------W",
    "DK2": "10YDK-2--------M",
}


def _format_ts(dt: datetime) -> str:
    """Format datetime for eSett API: yyyy-MM-dd'T'HH:mm:ss.000Z"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


class EsettClient:
    def __init__(self, base_url: str = ESETT_BASE_URL) -> None:
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self._base_url)
        return self._client

    async def fetch_load_profile(
        self,
        mba: str,
        start: datetime,
        end: datetime,
        mga: str | None = None,
    ) -> list[dict[str, object]]:
        """Fetch load profile data from eSett.

        Args:
            mba: MBA short name (e.g. "SE1"). Translated to EIC code internally.
            start: Start datetime (UTC).
            end: End datetime (UTC).
            mga: Optional MGA EIC code filter.

        Returns:
            List of load profile data points, or empty list on 204.

        Raises:
            KeyError: If mba is not in MBA_EIC_CODES.
            httpx.HTTPStatusError: On non-200/204 responses.
        """
        eic_code = MBA_EIC_CODES[mba]
        params: dict[str, str] = {
            "start": _format_ts(start),
            "end": _format_ts(end),
            "mba": eic_code,
        }
        if mga is not None:
            params["mga"] = mga

        client = await self._get_client()
        response = await client.get("/EXP18/LoadProfile", params=params)

        if response.status_code == 204:
            return []

        response.raise_for_status()
        result: list[dict[str, object]] = response.json()
        return result

    async def _fetch_dataset(
        self, path: str, mba: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]:
        """Fetch a dataset from eSett by path, translating MBA to EIC code."""
        eic_code = MBA_EIC_CODES[mba]
        params: dict[str, str] = {
            "start": _format_ts(start),
            "end": _format_ts(end),
            "mba": eic_code,
        }
        client = await self._get_client()
        response = await client.get(path, params=params)
        if response.status_code == 204:
            return []
        response.raise_for_status()
        result: list[dict[str, object]] = response.json()
        return result

    async def fetch_production(
        self, mba: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]:
        """Fetch hourly production data from /EXP16/Volumes."""
        return await self._fetch_dataset("/EXP16/Volumes", mba, start, end)

    async def fetch_consumption(
        self, mba: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]:
        """Fetch hourly consumption data from /EXP15/Consumption."""
        return await self._fetch_dataset("/EXP15/Consumption", mba, start, end)

    async def fetch_prices(
        self, mba: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]:
        """Fetch hourly imbalance prices from /EXP14/Prices."""
        return await self._fetch_dataset("/EXP14/Prices", mba, start, end)

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
