# Contributing

Contributions are welcome through issues and pull requests.

## Workflow

1. Open an issue for significant changes before implementation.
2. Fork the official repository for the purpose of preparing the contribution.
3. Create a focused branch.
4. Add or update tests and documentation.
5. Run the validation commands below.
6. Submit a pull request with the problem, approach, test evidence, and security impact.

## Validation

```bash
python -m compileall app scripts alembic
node --check app/static/dashboard.js
node --check app/static/exposure.js
node --check app/static/assessment.js
node --check app/static/intelligence.js
```

Do not submit credentials, customer data, internal hostnames, private URLs, or proprietary intelligence sources.

Contributions are subject to the project license and are accepted at the maintainers' discretion.
