import re
from urllib.parse import urlparse
import httpx
from app.collectors.base import Candidate
from app.source_registry import VENDORS
from app.config import settings

DOMAIN_RE = re.compile(r"(?<![A-Za-z0-9_-])(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}(?![A-Za-z0-9_-])")

def under_root(host: str, roots: list[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == r or host.endswith("." + r) for r in roots)

async def collect_vendor_docs() -> list[Candidate]:
    out: dict[tuple[str, str], Candidate] = {}
    headers = {"User-Agent": "AI-Enumerator/0.2 (+security-research)"}

    async with httpx.AsyncClient(
        timeout=settings.http_timeout,
        follow_redirects=True,
        headers=headers,
    ) as client:
        for vendor in VENDORS:
            roots = [x.lower() for x in vendor["root_domains"]]
            for source in vendor["docs"]:
                try:
                    r = await client.get(source)
                    r.raise_for_status()
                except Exception:
                    continue

                # Limit parsing to first 2 MiB to prevent unexpectedly huge responses.
                body = r.text[:2_000_000]
                candidates = set(DOMAIN_RE.findall(body))
                final_host = (urlparse(str(r.url)).hostname or "").lower()
                if final_host:
                    candidates.add(final_host)

                for host in candidates:
                    host = host.lower().rstrip(".")
                    if not under_root(host, roots):
                        continue
                    key = (vendor["vendor"], host)
                    out[key] = Candidate(
                        value=host,
                        kind="domain",
                        vendor=vendor["vendor"],
                        category=vendor["category"],
                        source=source,
                        confidence=90,
                        evidence=f"Official vendor documentation referenced {host}",
                    )
    return list(out.values())
