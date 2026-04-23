# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Service Does

Biblib is the ADS library service. It manages bibliographic libraries — users can create, share, and collaborate on collections of bibcodes (paper identifiers). It enforces a permission model (read/write/admin/owner), validates bibcodes against Solr, tracks change history via SQLAlchemy-Continuum, and supports library imports from Classic ADS and ADS 2.0.

## Commands

```bash
# Install dependencies
python3 -m venv python && source python/bin/activate
python -m pip install "pip==24" setuptools==57.5.0 wheel
pip install -e ".[dev]"

# Database setup (Docker)
docker run -d -e POSTGRES_USER="postgres" -e POSTGRES_PASSWORD="postgres" \
  -p 5432:5432 --name postgres postgres:12.6
docker exec -it postgres psql -U postgres -c "CREATE ROLE biblib_service WITH LOGIN PASSWORD 'biblib_service';"
docker exec -it postgres psql -U postgres -c "CREATE DATABASE biblib_service;"
docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE biblib_service TO biblib_service;"

# Apply migrations
export PYTHONPATH=$(pwd):$PYTHONPATH
alembic upgrade head

# Run service (port 4000)
python wsgi.py

# Run all tests
pytest

# Run a single test file
pytest biblib/tests/unit_tests/test_webservices.py

# Run a single test
pytest biblib/tests/unit_tests/test_webservices.py::TestClassName::test_method_name

# Lint (run after major edits)
flake8 biblib/
black --check biblib/
isort --check-only biblib/

# Auto-fix formatting
black biblib/
isort biblib/
```

## Architecture

### Stack
- Python 3.12 (local dev + CI unit tests), Flask, Flask-RESTful, SQLAlchemy 1.4, Alembic, PostgreSQL
- Runtime container currently builds on Python 3.8 (tailor base image — see "Deployment / runtime image" below)

### API Resources
| Resource class | Route | Purpose |
|---|---|---|
| `UserView` | `GET/POST /libraries` | List and create libraries |
| `LibraryView` | `GET /libraries/<lib>` | Retrieve library contents |
| `DocumentView` | `POST/DELETE/PUT /documents/<lib>` | Add, remove, update bibcodes |
| `NotesView` | `GET/POST/DELETE/PUT /notes/<lib>/<doc>` | Per-bibcode notes |
| `PermissionView` | `GET/POST /permissions/<lib>` | Manage user access |
| `TransferView` | `POST /transfer/<lib>` | Transfer library ownership |
| `QueryView` | `GET/POST /query/<lib>` | Library as Solr query / bigquery |
| `OperationsView` | `POST /libraries/operations/<lib>` | Batch operations (e.g. toggle public) |
| `ClassicView` | `GET /classic` | Import from Classic ADS |
| `TwoPointOhView` | `GET /twopointoh` | Import from ADS 2.0 |

Key files:
- `biblib/views/` — one file per resource class
- `biblib/views/base_view.py` — `BaseView` with shared helpers (permission checks, user resolution)
- `biblib/views/http_errors.py` — centralized HTTP error definitions
- `biblib/models.py` — `User`, `Library`, `Notes`, `Permissions` models; custom `GUID` column type
- `biblib/client.py` — HTTP client wrapper (auto-injects Authorization header)
- `biblib/config.py` — all configuration keys
- `biblib/emails.py` — email notification templates

### Permission Model
Permissions are stored as a JSON object on the `Permissions` row: `{read: bool, write: bool, admin: bool, owner: bool}`. All write/delete/admin operations check permissions in `BaseView` before proceeding. Only one user may hold `owner`.

### Versioning
`Library` and `Notes` records are versioned via SQLAlchemy-Continuum. Every mutation creates a history entry automatically. This is configured at model definition time, not in migrations.

### External Service Dependencies
- **Solr:** `/v1/search/query`, `/v1/bigquery` — bibcode validation and library-as-query execution
- **User API:** `/v1/user/<uid>` — email lookup (used for permission notifications)
- **Classic / 2.0 import APIs:** configured via `BIBLIB_CLASSIC_SERVICE_URL`, `BIBLIB_TWOPOINTOH_SERVICE_URL`

### Authentication
Bearer token via `Authorization` header; user identity from `X-api-uid` header. `client.py` auto-injects the service token for outbound calls.

### Key Config Values (`biblib/config.py`)
- `BIBLIB_SOLR_SEARCH_URL`, `BIBLIB_SOLR_BIG_QUERY_URL`
- `BIBLIB_USER_EMAIL_ADSWS_API_URL`
- `BIBLIB_MAX_ROWS=2000`, `BIGQUERY_MAX_ROWS=200`, `BIBLIB_SOLR_BIG_QUERY_MIN=10`

## Tests

- `biblib/tests/functional_tests/` — end-to-end workflow tests
- `biblib/tests/unit_tests/test_webservices.py` — REST endpoint tests
- `biblib/tests/unit_tests/test_views.py` — business logic tests
- Test factories use Factory-Boy and Faker; database isolation via `testing.postgresql`

## Database Migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
```

Migration versions are in `alembic/versions/`.

## CI / Docker

- GitHub Actions (`.github/workflows/python_actions.yml`): Python 3.12, `py.test`, Coveralls
- `docker-compose.yaml` runs the full test stack (biblib + postgres 12.6) on port 4000
- Local `Dockerfile` (`FROM python:3.12.8`) is for local development only — **not used by the deployed tailor pipeline**

## Deployment / runtime image

Deployed biblib containers are built by the ADS tailor pipeline, **not** by the repo's local `Dockerfile`. The tailor pipeline ignores the repo Dockerfile and uses its own base image stack defined in `adsabs/BeeHive/images/common/`:

```
ubuntu:20.04
  ↓ apt install python3 (= Python 3.8, Ubuntu 20.04 default)
  ↓ source-build Python 3.10.13 (/usr/local/bin/python3.10, pip3.10)
tailor:base-image-v0.1.0
  ↓ pip2/pip3/pip3.10 install gunicorn/gevent/supervisor/psycopg2
tailor:base-microimage-v0.2.1
  ↓ BeeHive/images/common/biblib/Dockerfile:
  ↓ RUN pip3 install .      ← resolves to Python 3.8
biblib runtime container
```

### Constraint this creates

Runtime dependencies in `pyproject.toml` must install on Python 3.8, regardless of which Python we use locally. Packages that require Python ≥3.9 (e.g. `markupsafe==3.0.3`, `psycopg2-binary==2.9.11`) will **break the tailor build** with `ERROR: Could not find a version that satisfies the requirement ...`. Dev-only deps are not affected — tailor runs `pip3 install .`, not `pip3 install -e ".[dev]"`.

### Why this isn't fixed yet

The tailor base-image stack was built before the Python 3.12 migration started. To fully honor "biblib runs on Python 3.12" in deployment, the tailor stack needs Python 3.12 added. That's outside this repo.

### What's required to make the tailor stack Python 3.12

Three changes in `adsabs/BeeHive`, in order:

1. **`images/common/base-image/Dockerfile`** — add Python 3.12 source build, mirroring the existing 3.10 block. Installs `/usr/local/bin/python3.12` + `pip3.12`. Tag as `tailor:base-image-v0.2.0`.

2. **`images/common/base-microimage/Dockerfile`** — base on the new `base-image-v0.2.0` and add:
   ```
   RUN pip3.12 install --upgrade setuptools
   RUN pip3.12 install --upgrade gunicorn gevent supervisor psycogreen psycopg2 json-logging-py
   RUN mv /usr/local/bin/gunicorn /usr/local/bin/gunicorn3.12
   ```
   Tag as `tailor:base-microimage-v0.3.0`.

3. **`images/common/biblib/Dockerfile`** — update `FROM` to the new microimage tag, change `pip3 install .` → `pip3.12 install .`, and wire gunicorn3.12 in `root/`.

After (1) and (2) land, every other service can migrate with just step (3) — a one-line Dockerfile change.

### Alternative considered

Upgrading Ubuntu 20.04 → 24.04 in `base-image` removes the source-build dance (24.04 ships Python 3.12 via apt). Cleaner long-term, but wider blast radius (breaks any service that depends on 20.04-specific apt packages). Defer to the tailor-modernization initiative.

### Interim policy for biblib and sibling services

- Keep runtime pins Python-3.8-compatible until the tailor stack supports 3.12
- Local venvs stay on 3.12 so we catch 3.12-specific issues early
- Document each temporarily-downgraded pin in the PR description so we know what to re-bump once the tailor work is done

### Known Python-3.8-incompatible pins currently avoided

| Package | Want | Using | Re-bump when |
|---|---|---|---|
| markupsafe | 3.0.3 | 2.1.5 | tailor → Python 3.12 |
| psycopg2-binary | 2.9.11 | 2.9.9 | tailor → Python 3.12 |

(These are the ones we've hit so far; more may surface for other services during Batch 2+ migrations.)
