# Architecture

AI Enumerator is a Docker Compose application built around a FastAPI API, PostgreSQL, Redis, Celery workers and Celery Beat.

## Components

```text
Browser
  |
FastAPI API
  |
  +-- PostgreSQL  -> catalog, observations, probes, scans, results, users
  +-- Redis       -> Celery broker/backend
  +-- Worker      -> background collection and scan tasks
  +-- Beat        -> scheduled enrichment and scans
```

## Core domains

### Intelligence

Maintains GenAI destination attribution, evidence and confidence. Sources are curated seed data and enrichment collectors.

### Exposure

Tests cataloged destinations from a probe location using DNS, TCP/443, TLS and HTTP.

### Assessment

Derives scores, historical change, probe comparison and reports from stored scan evidence.

## Data flow

```text
Seed + collectors
      |
Intelligence catalog
      |
Exposure targets
      |
Probe measurement
      |
Exposure results
      |
Assessment / reports / policy simulation
```

The architecture intentionally separates "this destination belongs to a GenAI ecosystem" from "this destination is reachable from this network."
