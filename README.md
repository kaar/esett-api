# eSett API Proxy (Expektra)

Time series data platform for Nordic energy market data from eSett.
API proxy that caches eSett Open Data responses in TimescaleDB.

Hosted at [expektra.nettelbladt.dev](https://expektra.nettelbladt.dev)

## Run locally

```sh
docker compose up
```

The API will be available at http://localhost:8000.

## Development

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --dev
make all        # format, lint, check, test
```
