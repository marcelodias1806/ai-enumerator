import asyncio
from app.db import SessionLocal
from app.models import AssetKind, Category, SourceType
from app.services.ingest import ingest_candidate
from app.collectors.vendor_docs import collect_vendor_docs
from app.collectors.crtsh import collect_crtsh

async def run_all():
    batches = [
        (SourceType.vendor_docs, await collect_vendor_docs()),
        (SourceType.certificate_transparency, await collect_crtsh()),
    ]

    stats = {"observed": 0, "collectors": {}}
    with SessionLocal() as db:
        for source_type, candidates in batches:
            stats["collectors"][source_type.value] = len(candidates)
            for c in candidates:
                ingest_candidate(
                    db,
                    kind=AssetKind(c.kind),
                    value=c.value,
                    vendor=c.vendor,
                    category=Category(c.category),
                    source_type=source_type,
                    source_ref=c.source,
                    source_confidence=c.confidence,
                    evidence=c.evidence,
                )
                stats["observed"] += 1
    return stats

def run_sync():
    return asyncio.run(run_all())
