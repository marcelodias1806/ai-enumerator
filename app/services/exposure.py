import asyncio
import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AIAsset, Action, AssetKind, Category, Probe, ProbeType,
    ExposureScan, ExposureResult, ExposureStatus, utcnow_naive
)

SCANNER_VERSION = "1.0"

def exposure_targets(db: Session):
    return list(db.scalars(
        select(AIAsset)
        .where(
            AIAsset.kind == AssetKind.domain,
            AIAsset.action != Action.ignore,
        )
        .order_by(AIAsset.vendor, AIAsset.category, AIAsset.value)
        .limit(settings.exposure_max_targets)
    ))


async def _tcp_tls_http(host: str, category: Category | None = None):
    import json
    import dns.resolver

    started = time.perf_counter()
    result = {
        "dns_ok": False, "tcp_ok": False, "tls_ok": False, "http_ok": False,
        "http_status": None, "resolved_ip": None, "latency_ms": None, "error": None,
        "failure_reason": None, "dns_cname": None,
        "tls_version": None, "tls_cipher": None, "tls_issuer": None, "tls_subject": None,
        "http_server": None, "http_location": None, "http_content_type": None,
        "redirect_chain": None, "exposure_confidence": 0,
    }

    # DNS A/AAAA via system resolver, plus best-effort CNAME evidence.
    try:
        infos = await asyncio.get_running_loop().run_in_executor(
            None, lambda: socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        )
        if not infos:
            result["error"] = "dns_no_records"
            result["failure_reason"] = "DNS_NO_RECORDS"
            return result
        result["dns_ok"] = True
        result["resolved_ip"] = infos[0][4][0]
        result["exposure_confidence"] = 20
        try:
            cname_ans = await asyncio.get_running_loop().run_in_executor(
                None, lambda: dns.resolver.resolve(host, "CNAME", lifetime=settings.exposure_tcp_timeout)
            )
            if cname_ans:
                result["dns_cname"] = str(cname_ans[0].target).rstrip(".")
        except Exception:
            pass
    except socket.gaierror:
        result["error"] = "dns:gaierror"
        result["failure_reason"] = "DNS_RESOLUTION_FAILED"
        return result
    except Exception as exc:
        result["error"] = f"dns:{type(exc).__name__}"
        result["failure_reason"] = "DNS_ERROR"
        return result

    # TCP/443
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, 443), timeout=settings.exposure_tcp_timeout
        )
        result["tcp_ok"] = True
        result["exposure_confidence"] = 40
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
    except asyncio.TimeoutError:
        result["error"] = "tcp:timeout"
        result["failure_reason"] = "TCP_TIMEOUT"
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return result
    except ConnectionRefusedError:
        result["error"] = "tcp:refused"
        result["failure_reason"] = "TCP_REFUSED"
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return result
    except Exception as exc:
        result["error"] = f"tcp:{type(exc).__name__}"
        result["failure_reason"] = "TCP_CONNECT_ERROR"
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return result

    # TLS metadata
    try:
        ctx = ssl.create_default_context()
        if not settings.exposure_verify_tls:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, 443, ssl=ctx, server_hostname=host),
            timeout=settings.exposure_tcp_timeout,
        )
        ssl_obj = writer.get_extra_info("ssl_object")
        if ssl_obj:
            result["tls_version"] = ssl_obj.version()
            cipher = ssl_obj.cipher()
            if cipher:
                result["tls_cipher"] = cipher[0]
            cert = ssl_obj.getpeercert() or {}
            result["tls_subject"] = ", ".join("=".join(x) for item in cert.get("subject", []) for x in item)
            result["tls_issuer"] = ", ".join("=".join(x) for item in cert.get("issuer", []) for x in item)
        result["tls_ok"] = True
        result["exposure_confidence"] = 70
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
    except ssl.SSLCertVerificationError:
        result["error"] = "tls:verify_failed"
        result["failure_reason"] = "TLS_VERIFY_FAILED"
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return result
    except asyncio.TimeoutError:
        result["error"] = "tls:timeout"
        result["failure_reason"] = "TLS_TIMEOUT"
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return result
    except Exception as exc:
        result["error"] = f"tls:{type(exc).__name__}"
        result["failure_reason"] = "TLS_ERROR"
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        return result

    # HTTP HEAD with bounded redirect-chain capture; no model/content download.
    try:
        chain = []
        url = f"https://{host}/"
        async with httpx.AsyncClient(
            timeout=settings.exposure_http_timeout,
            follow_redirects=False,
            verify=settings.exposure_verify_tls,
            headers={"User-Agent": "AI-Enumerator-Exposure/1.0"},
        ) as client:
            for _ in range(settings.exposure_redirect_limit + 1):
                response = await client.head(url)
                result["http_status"] = response.status_code
                result["http_server"] = response.headers.get("server")
                result["http_location"] = response.headers.get("location")
                result["http_content_type"] = response.headers.get("content-type")
                chain.append({"url": url, "status": response.status_code, "location": response.headers.get("location")})
                if response.status_code not in {301,302,303,307,308} or not response.headers.get("location"):
                    break
                try:
                    from urllib.parse import urljoin
                    next_url = urljoin(url, response.headers["location"])
                    # Stay on HTTPS only; scanner never follows to non-HTTPS.
                    if not next_url.lower().startswith("https://"):
                        break
                    url = next_url
                except Exception:
                    break
            result["redirect_chain"] = json.dumps(chain, ensure_ascii=False)
            result["http_ok"] = result["http_status"] is not None and 100 <= result["http_status"] < 600
            if result["http_ok"]:
                result["exposure_confidence"] = 95
                result["failure_reason"] = None
            elif result["http_status"] is not None:
                result["failure_reason"] = f"HTTP_{result['http_status']}"
    except httpx.TimeoutException:
        result["error"] = "http:timeout"
        result["failure_reason"] = "HTTP_TIMEOUT"
    except Exception as exc:
        result["error"] = f"http:{type(exc).__name__}"
        result["failure_reason"] = "HTTP_ERROR"

    result["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return result

def classify_status(r: dict) -> ExposureStatus:
    if r["http_ok"]:
        return ExposureStatus.reachable
    if r["tls_ok"] or r["tcp_ok"]:
        return ExposureStatus.partial
    if r["dns_ok"] and not r["tcp_ok"]:
        return ExposureStatus.blocked
    if not r["dns_ok"]:
        return ExposureStatus.failed
    return ExposureStatus.unknown

async def run_server_scan(db: Session, probe_name: str = "AI Enumerator Server") -> ExposureScan:
    probe = db.scalar(select(Probe).where(Probe.name == probe_name))
    if not probe:
        probe = Probe(
            name=probe_name,
            probe_type=ProbeType.server,
            network_label="Server egress",
            description="Built-in server-side exposure probe",
        )
        db.add(probe)
        db.commit()
        db.refresh(probe)

    probe.last_seen_at = utcnow_naive()
    scan = ExposureScan(probe_id=probe.id, started_at=utcnow_naive(), scanner_version=SCANNER_VERSION)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    targets = exposure_targets(db)
    scan.target_count = len(targets)
    db.commit()

    sem = asyncio.Semaphore(settings.exposure_scan_concurrency)

    async def one(asset):
        async with sem:
            raw = await _tcp_tls_http(asset.value, asset.category)
            status = classify_status(raw)
            return asset, raw, status

    results = await asyncio.gather(*(one(a) for a in targets))

    counters = {s: 0 for s in ExposureStatus}
    for asset, raw, status in results:
        counters[status] += 1
        db.add(ExposureResult(
            scan_id=scan.id,
            asset_id=asset.id,
            checked_at=utcnow_naive(),
            destination=asset.value,
            vendor=asset.vendor,
            category=asset.category,
            status=status,
            dns_ok=raw["dns_ok"],
            tcp_ok=raw["tcp_ok"],
            tls_ok=raw["tls_ok"],
            http_ok=raw["http_ok"],
            http_status=raw["http_status"],
            latency_ms=raw["latency_ms"],
            resolved_ip=raw["resolved_ip"],
            error=raw["error"],
            failure_reason=raw["failure_reason"],
            dns_cname=raw["dns_cname"],
            tls_version=raw["tls_version"],
            tls_cipher=raw["tls_cipher"],
            tls_issuer=raw["tls_issuer"],
            tls_subject=raw["tls_subject"],
            http_server=raw["http_server"],
            http_location=raw["http_location"],
            http_content_type=raw["http_content_type"],
            redirect_chain=raw["redirect_chain"],
            exposure_confidence=raw["exposure_confidence"],
        ))

    scan.reachable_count = counters[ExposureStatus.reachable]
    scan.blocked_count = counters[ExposureStatus.blocked]
    scan.partial_count = counters[ExposureStatus.partial]
    scan.failed_count = counters[ExposureStatus.failed]
    scan.finished_at = utcnow_naive()
    probe.last_seen_at = utcnow_naive()
    db.commit()
    db.refresh(scan)
    return scan

def latest_scan(db: Session, probe_id: int | None = None):
    stmt = select(ExposureScan).order_by(ExposureScan.started_at.desc())
    if probe_id:
        stmt = stmt.where(ExposureScan.probe_id == probe_id)
    return db.scalar(stmt.limit(1))

def scan_results(db: Session, scan_id: int):
    return list(db.scalars(
        select(ExposureResult)
        .where(ExposureResult.scan_id == scan_id)
        .order_by(ExposureResult.vendor, ExposureResult.category, ExposureResult.destination)
    ))

def exposure_overview(db: Session):
    scan = latest_scan(db)
    if not scan:
        return {
            "connected": True, "scan_id": None, "targets": 0, "reachable": 0,
            "blocked": 0, "partial": 0, "failed": 0, "last_scan": None,
        }
    return {
        "connected": True,
        "scan_id": scan.id,
        "targets": scan.target_count,
        "reachable": scan.reachable_count,
        "blocked": scan.blocked_count,
        "partial": scan.partial_count,
        "failed": scan.failed_count,
        "last_scan": scan.finished_at.isoformat() if scan.finished_at else None,
    }

def category_summary(db: Session, scan_id: int):
    rows = db.execute(
        select(
            ExposureResult.category,
            ExposureResult.status,
            func.count(ExposureResult.id)
        )
        .where(ExposureResult.scan_id == scan_id)
        .group_by(ExposureResult.category, ExposureResult.status)
    ).all()

    out = {}
    for category, status, count in rows:
        key = category.value
        out.setdefault(key, {"category": key, "total": 0, "reachable": 0, "blocked": 0, "partial": 0, "failed": 0})
        out[key]["total"] += count
        out[key][status.value] += count
    return sorted(out.values(), key=lambda x: x["total"], reverse=True)

def vendor_summary(db: Session, scan_id: int):
    rows = db.execute(
        select(
            ExposureResult.vendor,
            ExposureResult.status,
            func.count(ExposureResult.id)
        )
        .where(ExposureResult.scan_id == scan_id)
        .group_by(ExposureResult.vendor, ExposureResult.status)
    ).all()

    out = {}
    for vendor, status, count in rows:
        out.setdefault(vendor, {"vendor": vendor, "total": 0, "reachable": 0, "blocked": 0, "partial": 0, "failed": 0})
        out[vendor]["total"] += count
        out[vendor][status.value] += count
    return sorted(out.values(), key=lambda x: (x["reachable"], x["total"]), reverse=True)

def simulate_policy(db: Session, category_actions: dict[str, str]):
    scan = latest_scan(db)
    if not scan:
        return {"scan_id": None, "message": "no exposure scan available", "summary": {}}

    results = scan_results(db, scan.id)
    summary = {"block": 0, "monitor": 0, "allow": 0, "unchanged": 0}
    detail = {}
    for row in results:
        if row.status not in {ExposureStatus.reachable, ExposureStatus.partial}:
            continue
        action = category_actions.get(row.category.value, "unchanged")
        if action not in summary:
            action = "unchanged"
        summary[action] += 1
        detail.setdefault(row.category.value, {"reachable": 0, "proposed_action": action})
        detail[row.category.value]["reachable"] += 1

    return {
        "scan_id": scan.id,
        "current_reachable_or_partial": sum(summary.values()),
        "summary": summary,
        "categories": list(detail.values()),
    }
