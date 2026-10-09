#!/usr/bin/env python3
"""AI Enumerator remote exposure probe.

Usage:
  python ai_probe.py --server https://ai-enumerator.example --token <probe-token>

The agent receives only approved target metadata and performs DNS/TCP/TLS/HEAD checks.
It does not authenticate to AI services, send prompts, or download models.
"""
import argparse
import asyncio
import socket
import ssl
import time
from datetime import datetime, timezone

import httpx

VERSION = "1.0"

async def check(host, tcp_timeout=3, http_timeout=6):
    started = time.perf_counter()
    out = {
        "destination": host, "dns_ok": False, "tcp_ok": False, "tls_ok": False,
        "http_ok": False, "http_status": None, "latency_ms": None,
        "resolved_ip": None, "error": None,
    }
    try:
        infos = await asyncio.get_running_loop().run_in_executor(
            None, lambda: socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        )
        out["dns_ok"] = bool(infos)
        if infos:
            out["resolved_ip"] = infos[0][4][0]
    except Exception as exc:
        out["error"] = f"dns:{type(exc).__name__}"
        return out

    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(host, 443), timeout=tcp_timeout)
        out["tcp_ok"] = True
        w.close()
        await w.wait_closed()
    except Exception as exc:
        out["error"] = f"tcp:{type(exc).__name__}"
        return out

    try:
        ctx = ssl.create_default_context()
        r, w = await asyncio.wait_for(
            asyncio.open_connection(host, 443, ssl=ctx, server_hostname=host),
            timeout=tcp_timeout,
        )
        out["tls_ok"] = True
        w.close()
        await w.wait_closed()
    except Exception as exc:
        out["error"] = f"tls:{type(exc).__name__}"
        out["latency_ms"] = round((time.perf_counter()-started)*1000)
        return out

    try:
        async with httpx.AsyncClient(timeout=http_timeout, follow_redirects=False) as client:
            resp = await client.head(f"https://{host}/", headers={"User-Agent": f"AI-Enumerator-Probe/{VERSION}"})
            out["http_status"] = resp.status_code
            out["http_ok"] = True
    except Exception as exc:
        out["error"] = f"http:{type(exc).__name__}"

    out["latency_ms"] = round((time.perf_counter()-started)*1000)
    return out

def status_of(r):
    if r["http_ok"]: return "reachable"
    if r["tls_ok"] or r["tcp_ok"]: return "partial"
    if r["dns_ok"] and not r["tcp_ok"]: return "blocked"
    if not r["dns_ok"]: return "failed"
    return "unknown"

async def main(args):
    headers = {"X-Probe-Token": args.token}
    async with httpx.AsyncClient(timeout=20, verify=not args.insecure) as client:
        tr = await client.get(f"{args.server.rstrip('/')}/api/v1/probe/targets", headers=headers)
        tr.raise_for_status()
        targets = tr.json()

    sem = asyncio.Semaphore(args.concurrency)
    async def run(t):
        async with sem:
            r = await check(t["destination"], args.tcp_timeout, args.http_timeout)
            r["asset_id"] = t["asset_id"]
            r["status"] = status_of(r)
            return r

    started = datetime.now(timezone.utc)
    results = await asyncio.gather(*(run(t) for t in targets))
    finished = datetime.now(timezone.utc)

    payload = {
        "scan_started_at": started.isoformat(),
        "scan_finished_at": finished.isoformat(),
        "scanner_version": VERSION,
        "results": results,
    }
    async with httpx.AsyncClient(timeout=30, verify=not args.insecure) as client:
        rr = await client.post(
            f"{args.server.rstrip('/')}/api/v1/probe/results",
            headers=headers,
            json=payload,
        )
        rr.raise_for_status()
        print(rr.json())

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--server", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--concurrency", type=int, default=20)
    p.add_argument("--tcp-timeout", type=int, default=3)
    p.add_argument("--http-timeout", type=int, default=6)
    p.add_argument("--insecure", action="store_true")
    asyncio.run(main(p.parse_args()))
