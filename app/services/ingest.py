from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AIAsset, Observation, AssetKind, Category, Action, SourceType
from app.scoring import combined_confidence

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def normalize_value(kind: AssetKind, value: str) -> str:
    v = value.strip().lower()
    if kind == AssetKind.domain:
        v = v.strip(".")
        if v.startswith("*."):
            v = v[2:]
    return v

def ingest_candidate(db: Session, *, kind: AssetKind, value: str, vendor: str,
                     category: Category, source_type: SourceType, source_ref: str,
                     source_confidence: int, evidence: str | None = None) -> AIAsset:
    value = normalize_value(kind, value)
    now = _utcnow_naive()
    asset = db.scalar(select(AIAsset).where(AIAsset.kind == kind, AIAsset.value == value))
    if not asset:
        asset = AIAsset(kind=kind, value=value, vendor=vendor, category=category,
                        action=Action.review, confidence=0, approved=False,
                        first_seen=now, last_seen=now)
        db.add(asset); db.flush()
    else:
        asset.last_seen = now
    obs = db.scalar(select(Observation).where(
        Observation.asset_id == asset.id,
        Observation.source_type == source_type,
        Observation.source_ref == source_ref,
    ))
    if not obs:
        obs = Observation(asset_id=asset.id, source_type=source_type, source_ref=source_ref,
                          evidence=evidence, source_confidence=max(0,min(100,source_confidence)),
                          first_seen=now, last_seen=now)
        db.add(obs)
    else:
        obs.last_seen=now; obs.evidence=evidence or obs.evidence
        obs.source_confidence=max(obs.source_confidence,source_confidence)
    db.flush(); db.refresh(asset)
    asset.confidence=combined_confidence(asset.observations)
    db.commit(); db.refresh(asset)
    return asset
