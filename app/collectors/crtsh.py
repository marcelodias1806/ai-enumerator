import httpx
from app.collectors.base import Candidate
from app.source_registry import VENDORS
from app.config import settings

async def collect_crtsh() -> list[Candidate]:
    out: dict[tuple[str, str], Candidate] = {}
    headers = {"User-Agent": "AI-Enumerator/0.2 (+security-research)"}

    async with httpx.AsyncClient(timeout=settings.http_timeout, headers=headers) as client:
        for vendor in VENDORS:
            for root in vendor["root_domains"]:
                # CT is discovery evidence only; it never auto-blocks.
                url = "https://crt.sh/"
                try:
                    r = await client.get(url, params={"q": f"%.{root}", "output": "json"})
                    r.raise_for_status()
                    rows = r.json()
                except Exception:
                    continue

                for row in rows[:10000]:
                    for name in str(row.get("name_value", "")).splitlines():
                        name = name.strip().lower().lstrip("*.")
                        if not name or not (name == root or name.endswith("." + root)):
                            continue
                        key = (vendor["vendor"], name)
                        out[key] = Candidate(
                            value=name,
                            kind="domain",
                            vendor=vendor["vendor"],
                            category=vendor["category"],
                            source=f"crt.sh:{root}",
                            confidence=35,
                            evidence=f"Certificate Transparency observation for {name}",
                        )
    return list(out.values())
