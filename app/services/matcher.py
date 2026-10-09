from urllib.parse import urlparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AIAsset, AssetKind, Category

def host_from_destination(destination: str, url: str | None = None) -> str:
    raw = (url or destination or "").strip().lower()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        host = urlparse(raw).hostname or ""
    except Exception:
        host = destination.strip().lower().split("/")[0].split(":")[0]
    return host.rstrip(".")

def find_best_asset(db: Session, destination: str, url: str | None = None) -> AIAsset | None:
    host = host_from_destination(destination, url)
    if not host:
        return None

    exact = db.scalar(select(AIAsset).where(AIAsset.kind == AssetKind.domain, AIAsset.value == host))
    if exact:
        return exact

    parts = host.split(".")
    candidates = [".".join(parts[i:]) for i in range(1, max(1, len(parts)-1))]
    if candidates:
        rows = list(db.scalars(select(AIAsset).where(
            AIAsset.kind == AssetKind.domain,
            AIAsset.value.in_(candidates)
        )))
        if rows:
            return sorted(rows, key=lambda x: len(x.value), reverse=True)[0]

    return None
