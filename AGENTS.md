# AGENTS.md

This repository is `flowintel`, a Flask-based case management platform for security analysts with a Vite-built frontend asset pipeline.

## Scope

These instructions apply to the entire repository.

## Stack

- Backend: Python 3.12+, Flask, SQLAlchemy/Alembic-style migrations, pytest
- Frontend assets: Vite, plain JavaScript, Bootstrap, Vue components in selected areas
- Data/integrations: PostgreSQL or SQLite/MySQL/MariaDB, Valkey/Redis, MISP-related modules and taxonomies

## Repository Layout

- `app/`: main application code
- `app/templates/`: Jinja templates
- `app/static/js/`: frontend behavior
- `app/static/css/`: stylesheet assets
- `app/assets/`: Vite-managed source dependencies and build config
- `tests/`: pytest suite, generally organized by feature area
- `migrations/`: database migrations
- `conf/`: runtime configuration templates and local config files
- `modules/`: bundled MISP taxonomies, galaxies, and related resources
- `doc/`: user/admin/contributor documentation

## Local Setup

Typical bootstrap flow:

```bash
cp conf/config.py.default conf/config.py
cp conf/config_module.py.default conf/config_module.py
./install.sh
```

Notes:

- `install.sh` creates a local virtualenv in `env/`, installs Python dependencies with `uv`, installs frontend dependencies in `app/assets`, initializes git submodules, and creates runtime directories.
- `launch.sh` will also create `conf/config.py` and `conf/config_module.py` from their `.default` files if they are missing.
- Do not commit local `conf/config.py`.

## Common Commands

- Start dev app: `./launch.sh -l`
- Initialize dev database: `./launch.sh -i`
- Initialize prod database: `./launch.sh -ip`
- Recreate database: `./launch.sh -r`
- Run tests: `./launch.sh -t`
- Update taxonomies/galaxies: `./launch.sh -tg`
- Update MISP modules: `./launch.sh -mm`
- Build frontend assets: `cd app/assets && bun run build:static`

When changing a narrow area, prefer targeted pytest runs first, for example:

```bash
pytest tests/case/test_case_admin.py
```

## Development Guidance

- Keep changes localized to the relevant feature area under `app/` and `tests/`.
- Backend routes, forms, and feature logic are often split across sibling files such as `feature.py`, `feature_api.py`, and `feature_core.py`; inspect the whole feature folder before editing.
- UI changes usually require checking both Jinja templates under `app/templates/` and JS/CSS under `app/static/`.
- If you change Vite-managed frontend dependencies or source behavior, rebuild static assets from `app/assets`.
- If you add or change database behavior, check whether a migration is required in `migrations/versions/`.

## Testing Expectations

- Run the smallest relevant pytest subset while iterating.
- Before finishing a non-trivial change, run the most relevant test files or `./launch.sh -t` if the change is broad.
- Tests run with `FLASKENV=testing` through `launch.sh`.

## Repo-Specific Cautions

- The repo may already contain user changes. Do not revert unrelated modifications.
- `launch.sh` starts auxiliary processes such as notifications and MISP modules in `screen` sessions for some modes; avoid assuming a plain single-process dev server.
- Runtime directories like `history`, `history_test`, and `logs` are expected by scripts.
- Large vendor-like content under `modules/` should not be reformatted or edited unless the task explicitly targets it.

## Documentation

Relevant references:

- `README.md` for setup and operator commands
- `doc/contributor.md` for data model context
- `doc/user-manual.md` and `doc/installation-manual.md` for product behavior
