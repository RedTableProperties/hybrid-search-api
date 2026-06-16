# Web Data Discovery API

Async hybrid search service for satellite and geospatial data discovery.

![Deploy Documentation](https://github.com/RedTableProperties/hybrid-search-api/actions/workflows/deploy-docs.yml/badge.svg)
![OpenAPI Quality](https://github.com/RedTableProperties/hybrid-search-api/actions/workflows/openapi-quality.yml/badge.svg)
![Security Scan](https://github.com/RedTableProperties/hybrid-search-api/actions/workflows/security-scan.yml/badge.svg)

## Documentation

- **API reference (GitHub Pages):** https://redtableproperties.github.io/hybrid-search-api/
- **Custom domain (when configured):** https://docs.redtableproperties.co.za/

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

```bash
npm ci
npm run lint:api
npm run docs:api
pytest -q
```

## OpenAPI

Contract-driven API with Spectral lint, Redocly docs, Schemathesis contract tests, and GitHub Actions CI.