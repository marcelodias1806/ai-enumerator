# AI Enumerator

**GenAI Exposure Intelligence for networks.**

AI Enumerator catalogs GenAI-related destinations and validates, from a real network location, which services are reachable through DNS, TCP/443, TLS and HTTP. It keeps historical scans, compares exposure across probes, produces an exposure score, and generates management-ready PDF/CSV evidence.

> AI Enumerator measures **egress exposure**. It does not authenticate to AI services, send prompts, invoke models, or download model files.

## What it does

- GenAI intelligence catalog with vendor/category attribution and confidence
- automatic intelligence enrichment from official vendor sources and Certificate Transparency
- DNS, TCP/443, TLS and HTTP reachability evidence
- AI API and model-distribution exposure views
- historical scans and change detection
- multi-probe / multi-network comparison
- AI Egress Exposure Score
- executive PDF and technical CSV reports
- policy simulation and generic allow/block text feeds
- local authentication with viewer, analyst and admin roles

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

Edit `.env`. At minimum change the database password, JWT secret, bootstrap admin password and feed token. Keep `POSTGRES_PASSWORD` and the password embedded in `DATABASE_URL` identical.

Example:

```env
POSTGRES_PASSWORD=USE-A-STRONG-PASSWORD
DATABASE_URL=postgresql+psycopg://ai_enum:USE-A-STRONG-PASSWORD@db:5432/ai_enum
JWT_SECRET=USE-A-LONG-RANDOM-SECRET-AT-LEAST-32-BYTES
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=USE-A-STRONG-ADMIN-PASSWORD
FEED_TOKEN=USE-A-LONG-RANDOM-TOKEN
```

If port 8080 is already in use:

```env
AI_ENUMERATOR_PORT=8081
```

Build and start:

```bash
docker compose build --no-cache
docker compose up -d
```

First startup is zero-touch for the application data model:

1. Alembic upgrades the schema.
2. The bootstrap admin is created if missing.
3. The curated starter intelligence catalog is loaded idempotently.

Validate:

```bash
docker compose ps -a
docker compose run --rm migrate alembic current
```

Expected schema head:

```text
0004_public_v1 (head)
```

Open:

```text
http://localhost:8080/login
```

or the port selected with `AI_ENUMERATOR_PORT`.

## First scan

1. Open **Exposure**.
2. Click **Run Server Scan**.
3. Wait for the scan to finish.
4. Review **Reachable**, **Partial**, **Blocked** and **Failed**.
5. Open **Assessment** for score, history, comparison and report export.

The server scan measures reachability from the network location of the AI Enumerator Docker host.

## Intelligence enrichment

The initial curated catalog is only the baseline. AI Enumerator continuously enriches it.

Current collectors:

- **Official/vendor-controlled documentation** — extracts vendor-related hostnames referenced by configured sources.
- **Certificate Transparency** — discovers additional subdomains associated with configured vendor roots.

Discovered candidates are ingested with evidence, deduplicated, and assigned attribution confidence. Automated discovery does **not** automatically create a blocking decision; newly discovered assets remain subject to review.

Automatic enrichment is enabled by default and runs every 24 hours:

```env
INTELLIGENCE_AUTO_ENUMERATE=true
INTELLIGENCE_ENUMERATE_INTERVAL_SECONDS=86400
```

Run enrichment manually:

```bash
docker compose exec api python -m scripts.enrich
```

Then review **Intelligence** and run another Exposure scan. As the intelligence catalog grows, subsequent scans test the expanded target set.

See [Intelligence enrichment](docs/INTELLIGENCE.md) for the full data-flow, confidence and review model.

## Result semantics

| Status | Meaning |
|---|---|
| `reachable` | HTTP responded from the probe location |
| `partial` | transport/TLS evidence exists, but HTTP did not fully complete |
| `blocked` | DNS resolved, but TCP connectivity was blocked/unavailable |
| `failed` | DNS or another transport-stage error prevented useful reachability evidence |

HTTP responses such as `401`, `403` or `404` can still prove egress reachability because the remote service answered.

## Main screens

- **Overview** — executive exposure summary and key findings
- **Exposure** — technical scan evidence by destination, category and vendor
- **Assessment** — score, history, changes, probe comparison, PDF and CSV
- **Intelligence** — catalog review, confidence and evidence sources

## Data provenance

- **Exposure**: live probe measurements
- **Intelligence**: curated and collected destination catalog
- **Assessment**: metrics derived from exposure + intelligence

No demo activity data is required by the public workflow.

## Common operations

```bash
docker compose ps -a
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
docker compose logs migrate --no-color
```

Stop without deleting data:

```bash
docker compose down
```

Do **not** use `docker compose down -v` unless you intentionally want to delete persistent data.

## Upgrade

Preserve `.env` and Docker volumes:

```bash
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose run --rm migrate alembic current
```

## Documentation

- [Installation and deployment](docs/DEPLOYMENT.md)
- [Intelligence enrichment](docs/INTELLIGENCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scanning methodology](docs/SCANNING.md)
- [Policy feeds and simulation](docs/POLICY.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [License](LICENSE.md)
- [Trademarks](TRADEMARKS.md)

## Security notes

AI Enumerator performs controlled outbound validation against cataloged GenAI destinations. Review the scanner methodology before running it in a production network and follow your organization's authorization and change-management requirements.

Never commit `.env`, credentials, database dumps, probe tokens or generated secrets.

## License

The source is publicly available under the **AI Enumerator Community Source License 1.0**. It permits use and internal modification, and permits repository forks when used to contribute changes back to the official project. It does not permit independent redistribution, rebranding, sublicensing, or commercial use without written permission.

Because these restrictions go beyond OSI-approved open-source licenses, the project is accurately described as **source-available / community source**, not OSI Open Source.

## Project

AI Enumerator is maintained by **Tecnocorp Tecnologia**.

Official repository: https://github.com/marcelodias1806/ai-enumerator
