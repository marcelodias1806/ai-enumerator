# Installation and Deployment

## Requirements

- Docker Engine with Docker Compose v2
- 2+ vCPU and 4+ GB RAM recommended
- outbound DNS and HTTPS from the deployment network
- a modern browser

## Clone

```bash
git clone https://github.com/marcelodias1806/ai-enumerator.git
cd ai-enumerator
```

## Configure

```bash
cp .env.example .env
nano .env
```

At minimum replace the database password, JWT secret, bootstrap admin password and feed token.

For an HTTPS deployment, review `AUTH_COOKIE_SECURE` and place the application behind a TLS-enabled reverse proxy.

## Build and start

```bash
docker compose build --no-cache
docker compose up -d
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

## Load starter intelligence

```bash
docker compose exec api python -m scripts.seed
```

## Open

```text
http://localhost:8080/login
```

Use the admin credentials configured in `.env`.

## First scan

Open **Exposure** and click **Run Server Scan**.

The scan measures reachability from the network where the Docker host is running.

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

Do not use `docker compose down -v` unless you intentionally want to delete persistent volumes and database data.

## Upgrade

```bash
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose run --rm migrate alembic current
```
