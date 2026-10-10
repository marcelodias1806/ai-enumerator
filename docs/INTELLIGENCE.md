# Intelligence Enrichment

AI Enumerator separates **intelligence** from **exposure measurement**.

The intelligence layer answers:

> Which domains and endpoints are associated with GenAI vendors and ecosystems?

The exposure layer answers:

> Which of those destinations are reachable from this probe/network?

## Bootstrap catalog

On first startup, `scripts.seed` loads a curated baseline catalog. The seed is idempotent: running it again does not create duplicate assets.

## Enrichment pipeline

```text
curated seed
    |
    +--> official/vendor documentation collector
    |
    +--> Certificate Transparency collector
             |
             v
       candidate normalization
             |
       asset deduplication
             |
       evidence observation
             |
       confidence calculation
             |
       analyst review
             |
       expanded scan target set
```

## Official documentation collector

`app/collectors/vendor_docs.py` requests configured official/vendor-controlled sources and extracts hostnames. Only hostnames under configured vendor roots are accepted.

Current source configuration lives in:

```text
app/source_registry.py
```

A documentation-derived observation currently carries a higher source confidence than an unreviewed CT discovery because it is directly referenced by a configured vendor source.

## Certificate Transparency collector

`app/collectors/crtsh.py` uses Certificate Transparency data to discover subdomains under configured vendor roots.

CT is useful discovery evidence, but a certificate alone does not prove that a hostname is an active GenAI service. For that reason CT discoveries are lower-confidence evidence and do not become automatic blocking decisions.

## Deduplication

`app/services/ingest.py` normalizes candidate values and identifies assets by kind + normalized value. Repeated observations update the existing asset instead of creating duplicate rows.

Multiple evidence sources can be attached to the same asset.

## Confidence

Confidence describes **attribution/classification confidence**, not security risk.

A high confidence value means the evidence strongly supports that the asset belongs to the assigned vendor/category. It does not mean the asset is dangerous.

## Review model

Automatically discovered assets default to the review workflow. Discovery never means "block automatically."

Analyst decisions may classify an asset for allow, monitor, block, review, or ignore depending on the current policy model.

## Automatic schedule

The Celery Beat scheduler runs enrichment periodically.

Defaults:

```env
INTELLIGENCE_AUTO_ENUMERATE=true
INTELLIGENCE_ENUMERATE_INTERVAL_SECONDS=86400
```

Disable automatic enrichment:

```env
INTELLIGENCE_AUTO_ENUMERATE=false
```

## Manual enrichment

Run immediately:

```bash
docker compose exec api python -m scripts.enrich
```

The command prints how many candidates each collector observed.

## Why target counts grow

The initial scan may test only the curated seed. As enrichment discovers and ingests additional candidates, subsequent exposure scans operate against the expanded catalog.

Therefore a healthy installation may evolve from dozens of targets to a substantially larger set without changing the scanner itself.

## Safety boundary

The enrichment subsystem is deliberately constrained:

- configured vendor roots only;
- evidence-backed attribution;
- no automatic block decision from discovery;
- analyst review remains part of the workflow.

This keeps enumeration useful for defensive egress intelligence without treating every discovered subdomain as confirmed risky infrastructure.
