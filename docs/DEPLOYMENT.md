# Installation and Deployment

## Requirements

- Docker Engine with Docker Compose v2
- 2+ vCPU and 4+ GB RAM recommended
- outbound DNS and HTTPS from the deployment network
- a modern browser

## Clone and configure

```bash
git clone https://github.com/marcelodias1806/ai-enumerator.git
cd ai-enumerator
cp .env.example .env
nano .env
```

Set a strong `POSTGRES_PASSWORD` and use the same password in `DATABASE_URL`.

If port 8080 is occupied, set for example:

```env
AI_ENUMERATOR_BIND=127.0.0.1
AI_ENUMERATOR_PORT=8081
```

The container still listens on 8080 internally; only the host-side port changes.

## Build and start

```bash
docker compose build --no-cache
docker compose up -d
```

The migrate service performs three idempotent bootstrap operations:

```text
alembic upgrade head
bootstrap admin
load curated starter intelligence
```

Check status:

```bash
docker compose ps -a
```

Expected steady state:

- `db`: healthy
- `redis`: running
- `api`: running
- `worker`: running
- `beat`: running
- `migrate`: exited with code 0

## Validate schema

```bash
docker compose run --rm migrate alembic current
```

Expected:

```text
0004_public_v1 (head)
```

## Open

Default:

```text
http://localhost:8080/login
```

If `AI_ENUMERATOR_PORT=8081`:

```text
http://localhost:8081/login
```

## First scan

Open **Exposure** and click **Run Server Scan**.

## Enrichment

Automatic enrichment is enabled by default. To force it immediately:

```bash
docker compose exec api python -m scripts.enrich
```

Review the resulting candidates in **Intelligence**, then run another scan.

## Logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
docker compose logs migrate --no-color
```

## Stop without deleting data

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the database and Redis volumes.

## Upgrade

```bash
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose run --rm migrate alembic current
```

Preserve `.env` and volumes during normal upgrades.
