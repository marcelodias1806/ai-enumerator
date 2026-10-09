from datetime import datetime
from pydantic import BaseModel, Field
from app.models import (
    AssetKind, Category, Action, SourceType, UserRole
)

class AssetCreate(BaseModel):
    kind: AssetKind
    value: str
    vendor: str
    category: Category
    source_type: SourceType = SourceType.manual
    source_ref: str
    evidence: str | None = None
    source_confidence: int = Field(ge=0, le=100)

class DecisionIn(BaseModel):
    action: Action
    analyst_note: str | None = None

class ObservationOut(BaseModel):
    source_type: SourceType
    source_ref: str
    evidence: str | None
    source_confidence: int
    first_seen: datetime
    last_seen: datetime
    model_config = {"from_attributes": True}

class AssetOut(BaseModel):
    id: int
    kind: AssetKind
    value: str
    vendor: str
    category: Category
    action: Action
    confidence: int
    approved: bool
    analyst_note: str | None
    first_seen: datetime
    last_seen: datetime
    observations: list[ObservationOut] = []
    model_config = {"from_attributes": True}

class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    model_config = {"from_attributes": True}


class ProbeCreate(BaseModel):
    name: str
    network_label: str | None = None
    description: str | None = None

class ProbeOut(BaseModel):
    id: int
    name: str
    probe_type: str
    network_label: str | None
    description: str | None
    is_active: bool
    last_seen_at: datetime | None
    model_config = {"from_attributes": True}

class ExposureResultIn(BaseModel):
    asset_id: int
    destination: str
    status: str
    dns_ok: bool = False
    tcp_ok: bool = False
    tls_ok: bool = False
    http_ok: bool = False
    http_status: int | None = None
    latency_ms: int | None = None
    resolved_ip: str | None = None
    error: str | None = None

class ExposureBatchIn(BaseModel):
    scan_started_at: datetime
    scan_finished_at: datetime
    scanner_version: str = "1.0"
    results: list[ExposureResultIn]

class PolicySimulationIn(BaseModel):
    category_actions: dict[str, str]
