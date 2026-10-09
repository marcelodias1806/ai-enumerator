# AI Enumerator

**GenAI Exposure Intelligence for networks.**

AI Enumerator catalogs GenAI-related destinations and validates, from a real network location, which services are reachable through DNS, TCP/443, TLS and HTTP. It keeps historical scans, compares exposure across probes, produces an exposure score, and generates management-ready PDF/CSV evidence.

> AI Enumerator measures **egress exposure**. It does not authenticate to AI services, send prompts, invoke models, or download model files.

## What it does

- GenAI intelligence catalog with vendor/category attribution and confidence
- DNS, TCP/443, TLS and HTTP reachability evidence
- AI API and model-distribution exposure views
- Historical scans and change detection
- Multi-probe / multi-network comparison
- AI Egress Exposure Score
- Executive PDF and technical CSV reports
- Policy simulation and generic allow/block text feeds
- Local authentication with viewer, analyst and admin roles

## Requirements

- Docker Engine 24+ recommended
- Docker Compose v2
- 2 vCPU / 4 GB RAM recommended for a small deployment
- outbound DNS and HTTPS from the network where the probe runs

Linux, Windows + WSL2, and Docker Desktop are suitable for lab and evaluation deployments.

## Quick start

```bash
git clone https://github.com/marcelodias1806/ai-enumerator.git
cd ai-enumerator
cp .env.example .env
```

Edit `.env` and replace every value marked as a default or placeholder. At minimum change:

```env
DATABASE_URL=postgresql+psycopg://ai_enum:USE-A-STRONG-PASSWORD@db:5432/ai_enum
JWT_SECRET=USE-A-LONG-RANDOM-SECRET-AT-LEAST-32-BYTES
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=USE-A-STRONG-ADMIN-PASSWORD
FEED_TOKEN=USE-A-LONG-RANDOM-TOKEN
```

Build and start:

```bash
docker compose build --no-cache
docker compose up -d
```

Validate the database migration:

```bash
docker compose run --rm migrate alembic current
```

Expected schema head:

```text
0004_public_v1 (head)
```

Load the curated starter catalog:

```bash
docker compose exec api python -m scripts.seed
```

Open:

```text
http://localhost:8080/login
```

Log in with the credentials defined by `BOOTSTRAP_ADMIN_USERNAME` and `BOOTSTRAP_ADMIN_PASSWORD`.

## First scan

1. Open **Exposure**.
2. Click **Run Server Scan**.
3. Wait for the scan to finish.
4. Review **Reachable**, **Partial**, **Blocked** and **Failed** results.
5. Open **Assessment** for score, history, comparison and report export.

The server scan runs from the network location of the AI Enumerator container host. To compare other network segments, deploy additional probes from those locations.

## Result semantics

| Status | Meaning |
|---|---|
| `reachable` | HTTP responded from the probe location |
| `partial` | transport/TLS evidence exists, but HTTP did not fully complete |
| `blocked` | DNS resolved, but TCP connectivity was blocked/unavailable |
| `failed` | DNS or another transport-stage error prevented useful reachability evidence |

HTTP responses such as `401`, `403` or `404` can still prove egress reachability: the remote service answered the request even if the requested path was not authorized or did not exist.

## Main screens

- **Overview** — executive exposure summary and key findings
- **Exposure** — technical scan evidence by destination, category and vendor
- **Assessment** — score, history, changes, probe comparison, PDF and CSV
- **Intelligence** — catalog review, confidence and evidence sources

## Data provenance

- **Exposure**: live probe measurements
- **Intelligence**: curated and collected destination catalog
- **Assessment**: metrics derived from exposure + intelligence

No demo activity data is required by the public v1 workflow.

## Common operations

Check services:

```bash
docker compose ps -a
```

Follow API logs:

```bash
docker compose logs -f api
```

Follow migration logs:

```bash
docker compose logs migrate --no-color
```

Stop without deleting data:

```bash
docker compose down
```

Do **not** use `docker compose down -v` unless you intentionally want to delete persistent database data.

## Upgrade

Preserve `.env` and Docker volumes:

```bash
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose run --rm migrate alembic current
```

Never use `down -v` during a normal upgrade.

## Documentation

- [Installation and deployment](docs/DEPLOYMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scanning methodology](docs/SCANNING.md)
- [Policy feeds and simulation](docs/POLICY.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [License](LICENSE.md)
- [Trademarks](TRADEMARKS.md)

## Security notes

AI Enumerator performs controlled outbound validation against cataloged GenAI destinations. Review the scanner methodology before running it in a production network and follow your organization's authorization and change-management requirements.

Never commit `.env`, credentials, database dumps, probe tokens or generated secrets to the repository.

## License

The source is publicly available under the **AI Enumerator Community Source License 1.0**. It permits use and internal modification, and permits repository forks when used to contribute changes back to the official AI Enumerator project. It does not permit independent redistribution, rebranding, sublicensing, or commercial use without written permission.

Because these restrictions go beyond OSI-approved open-source licenses, the project is accurately described as **source-available / community source**, not OSI Open Source.

## Project

AI Enumerator is maintained by **Tecnocorp Tecnologia**.

Official repository: https://github.com/marcelodias1806/ai-enumerator
