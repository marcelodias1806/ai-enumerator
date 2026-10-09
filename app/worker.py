from celery import Celery
from app.config import settings

celery = Celery("ai_enumerator", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.beat_schedule = {
    "enumerate-ai-sources-daily": {"task":"app.worker.enumerate_sources","schedule":86400.0},
    "exposure-auto-scan": {"task":"app.worker.exposure_auto_scan","schedule":settings.exposure_auto_scan_interval_seconds},
}

@celery.task(name="app.worker.enumerate_sources")
def enumerate_sources():
    from app.collectors.runner import run_sync
    return run_sync()

@celery.task(name="app.worker.exposure_auto_scan")
def exposure_auto_scan():
    if not settings.exposure_auto_scan:
        return {"status": "skipped", "reason": "EXPOSURE_AUTO_SCAN=false"}
    import asyncio
    from app.db import SessionLocal
    from app.services.exposure import run_server_scan
    with SessionLocal() as db:
        scan = asyncio.run(run_server_scan(db))
        return {"status":"ok","scan_id":scan.id,"targets":scan.target_count,
                "reachable":scan.reachable_count,"partial":scan.partial_count,
                "blocked":scan.blocked_count,"failed":scan.failed_count}
