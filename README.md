# SkillGraph API

SkillGraph is a FastAPI application for workforce skill inventories, role readiness, learning plans, succession planning, and project staffing. Skills and roles are database records, so they can be added without changing the application code.

## Features

- Track employees, evidence-based skill ratings, proficiency confidence, and assessment history.
- Define roles and weighted skill requirements; rank employees by readiness and identify skill gaps.
- Compare skill supply with demand and estimate upskilling opportunities.
- Maintain critical-role succession benches and identify continuity risks.
- Match employees to project skill requirements while accounting for availability.
- Create learning plans from skill gaps and a learning-resource catalog.
- Optionally generate assessment questions, grade assessments, coach development plans, and extract skills using the Anthropic API.
- Browse the data in the bundled web UI and download streamed CSV reports.

## Run with Docker Compose

### Requirements

- Docker Engine with Docker Compose v2, or Docker Desktop with its WSL 2 backend.
- If using Docker Engine inside WSL, run the commands below from the **Ubuntu terminal**, not PowerShell.
- On this machine, Docker Engine runs inside Ubuntu WSL without Docker Desktop. If your Docker config refers to `docker-credential-desktop.exe`, remove that stale credential-helper setting as described in [Troubleshooting](#troubleshooting).
- Enough memory for the PostgreSQL configuration in `docker-compose.yml` (it sets `shared_buffers` to 1 GB).

### 1. Get the source and open the project directory

After cloning this repository:

```bash
cd skillgraph-api
```

In Ubuntu WSL, the path to a Windows checkout looks like this:

```bash
cd "/mnt/c/Users/<your-windows-user>/Downloads/skillgraph-api/skillgraph-api"
```

### 2. Create the demo dataset

On a fresh checkout, this creates the PostgreSQL container and persistent volume, then loads sample data:

```bash
docker compose run --build --rm api python -m scripts.demo
```

The demo script inserts 420 synthetic employees, 16 skills, 6 roles, project and learning data, and readiness scores. It is intended to run **once per empty database**. It stops with an error if the database already contains skills; it does not overwrite or clear data.

### 3. Start the app and open it

```bash
docker compose up --build -d
```

- Web UI: <http://localhost:8000>
- Interactive API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

When prompted by the web UI, enter the default local API key: `change-me`.

To follow API logs:

```bash
docker compose logs -f api
```

To stop the containers without deleting database data:

```bash
docker compose down
```

Compose stores PostgreSQL data in the `pgdata` volume, so it survives container restarts and `docker compose down`.

### Generate a larger synthetic dataset

Use this script instead of the demo script for a load test. It creates the configured numbers of employees, skills, roles, ratings, and readiness records:

```bash
docker compose run --build --rm api python -m scripts.seed --employees 1000000 --roles 50
```

The seed script expects an empty database too. Do not run it against a database with existing records.

### Reset the local database

**Destructive:** this permanently deletes the PostgreSQL data in this Compose project's `pgdata` volume. Stop the containers and remove the volume only if you really want to erase the database:

```bash
docker compose down --volumes
```

Then create the demo data again with the command in step 2. This command only targets the Compose project in the current directory; it does not remove volumes belonging to other Compose projects.

## Optional AI features

Core APIs, the web UI, and the demo work without an Anthropic API key. AI question generation, answer grading, coaching, and resume/profile skill extraction require one.

Create an untracked `.env` file in the project directory:

```dotenv
ANTHROPIC_API_KEY=your-key
```

Compose passes this value to the API container. Restart the API after changing it:

```bash
docker compose up -d api
```

Do not commit `.env` or paste API keys into source files. When AI endpoints are used, the relevant prompts and user-provided assessment/profile text are sent to Anthropic.

## Local development and tests

The application defaults to SQLite when `DATABASE_URL` is unset. With Python 3.12 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.demo
uvicorn app.main:app --reload
```

For Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The demo and development server use `./dev.db` by default. Run tests separately; the tests configure a temporary SQLite database:

```bash
python -m pytest
```

## Authentication and configuration

| Setting | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` for local Python; PostgreSQL in Compose | SQLAlchemy database connection |
| `API_KEY` | `change-me` in Compose; unset in local Python | If set, API requests must include `X-API-Key` |
| `ANTHROPIC_API_KEY` | Unset | Enables Anthropic-backed AI features |
| `DB_POOL` | `20` | SQLAlchemy PostgreSQL connection-pool size |
| `MIN_STORE_SCORE` | `0` | Minimum readiness score to retain in the readiness table |

The Compose defaults (`change-me` and the local PostgreSQL credentials in `docker-compose.yml`) are for development only. Do not expose this configuration to the internet or use it for production. Replace the API-key scheme with production-grade authentication and authorization before deployment.

For example, call an authenticated endpoint with curl:

```bash
curl -H "X-API-Key: change-me" http://localhost:8000/analytics/summary
```

## API overview

The full, interactive endpoint list and request/response schemas are available at <http://localhost:8000/docs>.

| Area | Example endpoints |
|---|---|
| Skills and roles | `POST /skills`, `GET /skills`, `POST /roles`, `PUT /roles/{role_id}/requirements` |
| Employees and ratings | `POST /employees/bulk`, `GET /employees`, `PUT /employees/{employee_id}/ratings`, `POST /ratings/bulk` |
| Readiness | `GET /employees/{employee_id}/readiness/{role_id}`, `GET /roles/{role_id}/candidates`, `GET /employees/{employee_id}/top-roles` |
| Workforce analytics | `GET /analytics/summary`, `GET /analytics/workforce-plan`, `GET /analytics/continuity-risks` |
| Assessments | `GET /skills/{skill_id}/questions`, `POST /employees/{employee_id}/assessments`, `GET /employees/{employee_id}/assessments` |
| Succession | `GET /succession`, `GET /succession/{role_id}`, `PUT /roles/{role_id}/critical` |
| Projects and availability | `POST /projects`, `GET /projects/{project_id}/staffing`, `PUT /employees/{employee_id}/availability` |
| Learning | `POST /learning`, `GET /learning`, `GET /employees/{employee_id}/development-plan/{role_id}` |
| CSV reports | `GET /reports/skill-matrix.csv`, `GET /reports/role-readiness.csv`, `GET /reports/workforce-plan.csv`, `GET /reports/succession.csv` |

## Project structure

```text
.
├── app/
│   ├── main.py          FastAPI app, authentication, request schemas, API endpoints, CSV reports
│   ├── models.py        SQLAlchemy database tables and indexes
│   ├── db.py            Database engine, sessions, and portable bulk upsert helper
│   ├── readiness.py     Set-based employee-to-role readiness calculations
│   ├── ai.py            Optional Anthropic assessment, coaching, and skill extraction
│   └── static/
│       └── index.html   Single-page web UI served by FastAPI
├── scripts/
│   ├── demo.py          Small realistic sample dataset; only for an empty database
│   └── seed.py          Configurable synthetic data generator/load test
├── tests/
│   └── test_api.py      API, readiness, pagination, succession, staffing, and report tests
├── Dockerfile           Python API image
├── docker-compose.yml   API and PostgreSQL services plus persistent database volume
└── requirements.txt     Python dependencies
```

### Data and readiness design

- Skills, roles, and role requirements are rows in tables rather than hard-coded application enums.
- Skill ratings are sparse: a row is stored for an employee/skill where there is evidence.
- Readiness is precomputed and stored in `role_readiness`; rating or requirement updates recalculate the affected people or role.
- The demo dataset is synthetic. Replace the sample API key, add proper authorization, configure migrations, and establish data-consent and retention policies before using real workforce data.

## Troubleshooting

### `Database already has data; use an empty database.`

The demo script intentionally refuses to seed a database that already has skills. Keep using the existing data, or reset the current local Compose database with the destructive reset steps above. Do not delete the volume if you need its current data.

### Docker reports `docker-credential-desktop.exe` is missing (Docker Engine inside WSL)

The WSL Docker CLI may be configured to use a Windows Docker Desktop credential helper even when Docker Desktop is not installed. If you do not use Docker Desktop, remove that stale setting from your WSL Docker config:

```bash
sed -i '/"credsStore"[[:space:]]*:[[:space:]]*"desktop\.exe"/d' ~/.docker/config.json
```

This removes only the `credsStore` entry; it does not delete Docker images, containers, volumes, or database data. Then run Compose normally:

```bash
docker compose up --build -d
```

### Port 5432 or 8000 is already in use

Another process or Compose project is using that host port. Stop the conflicting service, or change the relevant host-side port mapping in `docker-compose.yml` before starting this project.

### Database connection fails on first start

Check that PostgreSQL is running and ready before retrying:

```bash
docker compose ps
docker compose logs db
```

If you recently changed the schema, note that the app currently creates missing tables but does not migrate existing tables. For changed columns, use a fresh development database or add and run a proper migration before reusing existing data.

### PostgreSQL reports duplicate primary keys when adding employees or other records

Older demo and load-test scripts inserted explicit skill, role, employee, and project IDs without advancing PostgreSQL's auto-generated ID sequences. The current scripts synchronize these sequences after loading data. For a database populated by an older script, rebuild the API image and synchronize its sequences without deleting data:

```bash
docker compose up --build -d api
docker compose run --rm api python -c 'from app.db import SessionLocal, sync_postgres_sequences; from app.models import Employee, Project, Role, Skill; session=SessionLocal(); sync_postgres_sequences(session, [Skill, Role, Employee, Project]); session.commit(); session.close()'
```
# SkillGraph API

SkillGraph is a FastAPI application for workforce skill inventories, role readiness, learning plans, succession planning, and project staffing. Skills and roles are database records, so they can be added without changing the application code.

## Features

- Track employees, evidence-based skill ratings, proficiency confidence, and assessment history.
- Define roles and weighted skill requirements; rank employees by readiness and identify skill gaps.
- Compare skill supply with demand and estimate upskilling opportunities.
- Maintain critical-role succession benches and identify continuity risks.
- Match employees to project skill requirements while accounting for availability.
- Create learning plans from skill gaps and a learning-resource catalog.
- Optionally generate assessment questions, grade assessments, coach development plans, and extract skills using the Anthropic API.
- Browse the data in the bundled web UI and download streamed CSV reports.

## Run with Docker Compose

### Requirements

- Docker Engine with Docker Compose v2, or Docker Desktop with its WSL 2 backend.
- If using Docker Engine inside WSL, run the commands below from the **Ubuntu terminal**, not PowerShell.
- On this machine, Docker Engine runs inside Ubuntu WSL without Docker Desktop. If your Docker config refers to `docker-credential-desktop.exe`, remove that stale credential-helper setting as described in [Troubleshooting](#troubleshooting).
- Enough memory for the PostgreSQL configuration in `docker-compose.yml` (it sets `shared_buffers` to 1 GB).

### 1. Get the source and open the project directory

After cloning this repository:

```bash
cd skillgraph-api
```

In Ubuntu WSL, the path to a Windows checkout looks like this:

```bash
cd "/mnt/c/Users/<your-windows-user>/Downloads/skillgraph-api/skillgraph-api"
```

### 2. Create the demo dataset

On a fresh checkout, this creates the PostgreSQL container and persistent volume, then loads sample data:

```bash
docker compose run --build --rm api python -m scripts.demo
```

The demo script inserts 420 synthetic employees, 16 skills, 6 roles, project and learning data, and readiness scores. It is intended to run **once per empty database**. It stops with an error if the database already contains skills; it does not overwrite or clear data.

### 3. Start the app and open it

```bash
docker compose up --build -d
```

- Web UI: <http://localhost:8000>
- Interactive API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

When prompted by the web UI, enter the default local API key: `change-me`.

To follow API logs:

```bash
docker compose logs -f api
```

To stop the containers without deleting database data:

```bash
docker compose down
```

Compose stores PostgreSQL data in the `pgdata` volume, so it survives container restarts and `docker compose down`.

### Generate a larger synthetic dataset

Use this script instead of the demo script for a load test. It creates the configured numbers of employees, skills, roles, ratings, and readiness records:

```bash
docker compose run --build --rm api python -m scripts.seed --employees 1000000 --roles 50
```

The seed script expects an empty database too. Do not run it against a database with existing records.

### Reset the local database

**Destructive:** this permanently deletes the PostgreSQL data in this Compose project's `pgdata` volume. Stop the containers and remove the volume only if you really want to erase the database:

```bash
docker compose down --volumes
```

Then create the demo data again with the command in step 2. This command only targets the Compose project in the current directory; it does not remove volumes belonging to other Compose projects.

## Optional AI features

Core APIs, the web UI, and the demo work without an Anthropic API key. AI question generation, answer grading, coaching, and resume/profile skill extraction require one.

Create an untracked `.env` file in the project directory:

```dotenv
ANTHROPIC_API_KEY=your-key
```

Compose passes this value to the API container. Restart the API after changing it:

```bash
docker compose up -d api
```

Do not commit `.env` or paste API keys into source files. When AI endpoints are used, the relevant prompts and user-provided assessment/profile text are sent to Anthropic.

## Local development and tests

The application defaults to SQLite when `DATABASE_URL` is unset. With Python 3.12 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.demo
uvicorn app.main:app --reload
```

For Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The demo and development server use `./dev.db` by default. Run tests separately; the tests configure a temporary SQLite database:

```bash
python -m pytest
```

## Authentication and configuration

| Setting | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` for local Python; PostgreSQL in Compose | SQLAlchemy database connection |
| `API_KEY` | `change-me` in Compose; unset in local Python | If set, API requests must include `X-API-Key` |
| `ANTHROPIC_API_KEY` | Unset | Enables Anthropic-backed AI features |
| `DB_POOL` | `20` | SQLAlchemy PostgreSQL connection-pool size |
| `MIN_STORE_SCORE` | `0` | Minimum readiness score to retain in the readiness table |

The Compose defaults (`change-me` and the local PostgreSQL credentials in `docker-compose.yml`) are for development only. Do not expose this configuration to the internet or use it for production. Replace the API-key scheme with production-grade authentication and authorization before deployment.

For example, call an authenticated endpoint with curl:

```bash
curl -H "X-API-Key: change-me" http://localhost:8000/analytics/summary
```

## API overview

The full, interactive endpoint list and request/response schemas are available at <http://localhost:8000/docs>.

| Area | Example endpoints |
|---|---|
| Skills and roles | `POST /skills`, `GET /skills`, `POST /roles`, `PUT /roles/{role_id}/requirements` |
| Employees and ratings | `POST /employees/bulk`, `GET /employees`, `PUT /employees/{employee_id}/ratings`, `POST /ratings/bulk` |
| Readiness | `GET /employees/{employee_id}/readiness/{role_id}`, `GET /roles/{role_id}/candidates`, `GET /employees/{employee_id}/top-roles` |
| Workforce analytics | `GET /analytics/summary`, `GET /analytics/workforce-plan`, `GET /analytics/continuity-risks` |
| Assessments | `GET /skills/{skill_id}/questions`, `POST /employees/{employee_id}/assessments`, `GET /employees/{employee_id}/assessments` |
| Succession | `GET /succession`, `GET /succession/{role_id}`, `PUT /roles/{role_id}/critical` |
| Projects and availability | `POST /projects`, `GET /projects/{project_id}/staffing`, `PUT /employees/{employee_id}/availability` |
| Learning | `POST /learning`, `GET /learning`, `GET /employees/{employee_id}/development-plan/{role_id}` |
| CSV reports | `GET /reports/skill-matrix.csv`, `GET /reports/role-readiness.csv`, `GET /reports/workforce-plan.csv`, `GET /reports/succession.csv` |

## Project structure

```text
.
├── app/
│   ├── main.py          FastAPI app, authentication, request schemas, API endpoints, CSV reports
│   ├── models.py        SQLAlchemy database tables and indexes
│   ├── db.py            Database engine, sessions, and portable bulk upsert helper
│   ├── readiness.py     Set-based employee-to-role readiness calculations
│   ├── ai.py            Optional Anthropic assessment, coaching, and skill extraction
│   └── static/
│       └── index.html   Single-page web UI served by FastAPI
├── scripts/
│   ├── demo.py          Small realistic sample dataset; only for an empty database
│   └── seed.py          Configurable synthetic data generator/load test
├── tests/
│   └── test_api.py      API, readiness, pagination, succession, staffing, and report tests
├── Dockerfile           Python API image
├── docker-compose.yml   API and PostgreSQL services plus persistent database volume
└── requirements.txt     Python dependencies
```

### Data and readiness design

- Skills, roles, and role requirements are rows in tables rather than hard-coded application enums.
- Skill ratings are sparse: a row is stored for an employee/skill where there is evidence.
- Readiness is precomputed and stored in `role_readiness`; rating or requirement updates recalculate the affected people or role.
- The demo dataset is synthetic. Replace the sample API key, add proper authorization, configure migrations, and establish data-consent and retention policies before using real workforce data.

## Troubleshooting

### `Database already has data; use an empty database.`

The demo script intentionally refuses to seed a database that already has skills. Keep using the existing data, or reset the current local Compose database with the destructive reset steps above. Do not delete the volume if you need its current data.

### Docker reports `docker-credential-desktop.exe` is missing (Docker Engine inside WSL)

The WSL Docker CLI may be configured to use a Windows Docker Desktop credential helper even when Docker Desktop is not installed. If you do not use Docker Desktop, remove that stale setting from your WSL Docker config:

```bash
sed -i '/"credsStore"[[:space:]]*:[[:space:]]*"desktop\.exe"/d' ~/.docker/config.json
```

This removes only the `credsStore` entry; it does not delete Docker images, containers, volumes, or database data. Then run Compose normally:

```bash
docker compose up --build -d
```

### Port 5432 or 8000 is already in use

Another process or Compose project is using that host port. Stop the conflicting service, or change the relevant host-side port mapping in `docker-compose.yml` before starting this project.

### Database connection fails on first start

Check that PostgreSQL is running and ready before retrying:

```bash
docker compose ps
docker compose logs db
```

If you recently changed the schema, note that the app currently creates missing tables but does not migrate existing tables. For changed columns, use a fresh development database or add and run a proper migration before reusing existing data.

### PostgreSQL reports duplicate primary keys when adding employees or other records

Older demo and load-test scripts inserted explicit skill, role, employee, and project IDs without advancing PostgreSQL's auto-generated ID sequences. The current scripts synchronize these sequences after loading data. For a database populated by an older script, rebuild the API image and synchronize its sequences without deleting data:

```bash
docker compose up --build -d api
docker compose run --rm api python -c 'from app.db import SessionLocal, sync_postgres_sequences; from app.models import Employee, Project, Role, Skill; session=SessionLocal(); sync_postgres_sequences(session, [Skill, Role, Employee, Project]); session.commit(); session.close()'
```
# SkillGraph API

SkillGraph is a FastAPI application for workforce skill inventories, role readiness, learning plans, succession planning, and project staffing. Skills and roles are database records, so they can be added without changing the application code.

## Features

- Track employees, evidence-based skill ratings, proficiency confidence, and assessment history.
- Define roles and weighted skill requirements; rank employees by readiness and identify skill gaps.
- Compare skill supply with demand and estimate upskilling opportunities.
- Maintain critical-role succession benches and identify continuity risks.
- Match employees to project skill requirements while accounting for availability.
- Create learning plans from skill gaps and a learning-resource catalog.
- Optionally generate assessment questions, grade assessments, coach development plans, and extract skills using the Anthropic API.
- Browse the data in the bundled web UI and download streamed CSV reports.

## Run with Docker Compose

### Requirements

- Docker Engine with Docker Compose v2, or Docker Desktop with its WSL 2 backend.
- If using Docker Engine inside WSL, run the commands below from the **Ubuntu terminal**, not PowerShell.
- Enough memory for the PostgreSQL configuration in `docker-compose.yml` (it sets `shared_buffers` to 1 GB).

### 1. Get the source and open the project directory

After cloning this repository:

```bash
cd skillgraph-api
```

In Ubuntu WSL, the path to a Windows checkout looks like this:

```bash
cd "/mnt/c/Users/<your-windows-user>/Downloads/skillgraph-api/skillgraph-api"
```

### 2. Create the demo dataset

On a fresh checkout, this creates the PostgreSQL container and persistent volume, then loads sample data:

```bash
docker compose run --build --rm api python -m scripts.demo
```

The demo script inserts 420 synthetic employees, 16 skills, 6 roles, project and learning data, and readiness scores. It is intended to run **once per empty database**. It stops with an error if the database already contains skills; it does not overwrite or clear data.

### 3. Start the app and open it

```bash
docker compose up --build -d
```

- Web UI: <http://localhost:8000>
- Interactive API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

When prompted by the web UI, enter the default local API key: `change-me`.

To follow API logs:

```bash
docker compose logs -f api
```

To stop the containers without deleting database data:

```bash
docker compose down
```

Compose stores PostgreSQL data in the `pgdata` volume, so it survives container restarts and `docker compose down`.

### Generate a larger synthetic dataset

Use this script instead of the demo script for a load test. It creates the configured numbers of employees, skills, roles, ratings, and readiness records:

```bash
docker compose run --build --rm api python -m scripts.seed --employees 1000000 --roles 50
```

The seed script expects an empty database too. Do not run it against a database with existing records.

### Reset the local database

**Destructive:** this permanently deletes the PostgreSQL data in this Compose project's `pgdata` volume. Stop the containers and remove the volume only if you really want to erase the database:

```bash
docker compose down --volumes
```

Then create the demo data again with the command in step 2. This command only targets the Compose project in the current directory; it does not remove volumes belonging to other Compose projects.

## Optional AI features

Core APIs, the web UI, and the demo work without an Anthropic API key. AI question generation, answer grading, coaching, and resume/profile skill extraction require one.

Create an untracked `.env` file in the project directory:

```dotenv
ANTHROPIC_API_KEY=your-key
```

Compose passes this value to the API container. Restart the API after changing it:

```bash
docker compose up -d api
```

Do not commit `.env` or paste API keys into source files. When AI endpoints are used, the relevant prompts and user-provided assessment/profile text are sent to Anthropic.

## Local development and tests

The application defaults to SQLite when `DATABASE_URL` is unset. With Python 3.12 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.demo
uvicorn app.main:app --reload
```

For Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The demo and development server use `./dev.db` by default. Run tests separately; the tests configure a temporary SQLite database:

```bash
python -m pytest
```

## Authentication and configuration

| Setting | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` for local Python; PostgreSQL in Compose | SQLAlchemy database connection |
| `API_KEY` | `change-me` in Compose; unset in local Python | If set, API requests must include `X-API-Key` |
| `ANTHROPIC_API_KEY` | Unset | Enables Anthropic-backed AI features |
| `DB_POOL` | `20` | SQLAlchemy PostgreSQL connection-pool size |
| `MIN_STORE_SCORE` | `0` | Minimum readiness score to retain in the readiness table |

The Compose defaults (`change-me` and the local PostgreSQL credentials in `docker-compose.yml`) are for development only. Do not expose this configuration to the internet or use it for production. Replace the API-key scheme with production-grade authentication and authorization before deployment.

For example, call an authenticated endpoint with curl:

```bash
curl -H "X-API-Key: change-me" http://localhost:8000/analytics/summary
```

## API overview

The full, interactive endpoint list and request/response schemas are available at <http://localhost:8000/docs>.

| Area | Example endpoints |
|---|---|
| Skills and roles | `POST /skills`, `GET /skills`, `POST /roles`, `PUT /roles/{role_id}/requirements` |
| Employees and ratings | `POST /employees/bulk`, `GET /employees`, `PUT /employees/{employee_id}/ratings`, `POST /ratings/bulk` |
| Readiness | `GET /employees/{employee_id}/readiness/{role_id}`, `GET /roles/{role_id}/candidates`, `GET /employees/{employee_id}/top-roles` |
| Workforce analytics | `GET /analytics/summary`, `GET /analytics/workforce-plan`, `GET /analytics/continuity-risks` |
| Assessments | `GET /skills/{skill_id}/questions`, `POST /employees/{employee_id}/assessments`, `GET /employees/{employee_id}/assessments` |
| Succession | `GET /succession`, `GET /succession/{role_id}`, `PUT /roles/{role_id}/critical` |
| Projects and availability | `POST /projects`, `GET /projects/{project_id}/staffing`, `PUT /employees/{employee_id}/availability` |
| Learning | `POST /learning`, `GET /learning`, `GET /employees/{employee_id}/development-plan/{role_id}` |
| CSV reports | `GET /reports/skill-matrix.csv`, `GET /reports/role-readiness.csv`, `GET /reports/workforce-plan.csv`, `GET /reports/succession.csv` |

## Project structure

```text
.
├── app/
│   ├── main.py          FastAPI app, authentication, request schemas, API endpoints, CSV reports
│   ├── models.py        SQLAlchemy database tables and indexes
│   ├── db.py            Database engine, sessions, and portable bulk upsert helper
│   ├── readiness.py     Set-based employee-to-role readiness calculations
│   ├── ai.py            Optional Anthropic assessment, coaching, and skill extraction
│   └── static/
│       └── index.html   Single-page web UI served by FastAPI
├── scripts/
│   ├── demo.py          Small realistic sample dataset; only for an empty database
│   └── seed.py          Configurable synthetic data generator/load test
├── tests/
│   └── test_api.py      API, readiness, pagination, succession, staffing, and report tests
├── Dockerfile           Python API image
├── docker-compose.yml   API and PostgreSQL services plus persistent database volume
└── requirements.txt     Python dependencies
```

### Data and readiness design

- Skills, roles, and role requirements are rows in tables rather than hard-coded application enums.
- Skill ratings are sparse: a row is stored for an employee/skill where there is evidence.
- Readiness is precomputed and stored in `role_readiness`; rating or requirement updates recalculate the affected people or role.
- The demo dataset is synthetic. Replace the sample API key, add proper authorization, configure migrations, and establish data-consent and retention policies before using real workforce data.

## Troubleshooting

### `Database already has data; use an empty database.`

The demo script intentionally refuses to seed a database that already has skills. Keep using the existing data, or reset the current local Compose database with the destructive reset steps above. Do not delete the volume if you need its current data.

### Docker reports `docker-credential-desktop.exe` is missing (Docker Engine inside WSL)

This can happen when the WSL Docker CLI uses a Windows Docker Desktop credential helper that is not installed. For public images that do not require registry authentication, use a temporary empty Docker configuration for the command:

```bash
DOCKER_CONFIG="$(mktemp -d)" docker compose run --build --rm api python -m scripts.demo
```

### Port 5432 or 8000 is already in use

Another process or Compose project is using that host port. Stop the conflicting service, or change the relevant host-side port mapping in `docker-compose.yml` before starting this project.

### Database connection fails on first start

Check that PostgreSQL is running and ready before retrying:

```bash
docker compose ps
docker compose logs db
```

If you recently changed the schema, note that the app currently creates missing tables but does not migrate existing tables. For changed columns, use a fresh development database or add and run a proper migration before reusing existing data.
