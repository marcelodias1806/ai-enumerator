import enum
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, Enum, Integer, BigInteger, Text, Boolean, UniqueConstraint,
    ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class AssetKind(str, enum.Enum):
    domain = "domain"
    url = "url"

class Category(str, enum.Enum):
    genai_web = "genai_web"
    ai_api = "ai_api"
    ai_coding = "ai_coding"
    model_registry = "model_registry"
    model_cdn = "model_cdn"
    llm_runtime = "llm_runtime"
    enterprise_approved = "enterprise_approved"

class Action(str, enum.Enum):
    block = "block"
    monitor = "monitor"
    allow = "allow"
    review = "review"
    ignore = "ignore"

class SourceType(str, enum.Enum):
    manual = "manual"
    vendor_docs = "vendor_docs"
    certificate_transparency = "certificate_transparency"
    dns = "dns"
    github_official = "github_official"

class UserRole(str, enum.Enum):
    viewer = "viewer"
    analyst = "analyst"
    admin = "admin"

class AIAsset(Base):
    __tablename__ = "ai_assets"
    __table_args__ = (UniqueConstraint("kind", "value", name="uq_asset_kind_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[AssetKind] = mapped_column(Enum(AssetKind), nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[Category] = mapped_column(Enum(Category), nullable=False, index=True)
    action: Mapped[Action] = mapped_column(Enum(Action), default=Action.review, nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analyst_note: Mapped[str | None] = mapped_column(Text)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    observations: Mapped[list["Observation"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("asset_id", "source_type", "source_ref", name="uq_observation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("ai_assets.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    source_confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    asset: Mapped[AIAsset] = relationship(back_populates="observations")

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.viewer, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class ProbeType(str, enum.Enum):
    server = "server"
    agent = "agent"

class ExposureStatus(str, enum.Enum):
    reachable = "reachable"
    blocked = "blocked"
    partial = "partial"
    failed = "failed"
    unknown = "unknown"

class Probe(Base):
    __tablename__ = "probes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    probe_type: Mapped[ProbeType] = mapped_column(Enum(ProbeType), default=ProbeType.agent, nullable=False)
    network_label: Mapped[str | None] = mapped_column(String(256), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    token_hash: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)

class ExposureScan(Base):
    __tablename__ = "exposure_scans"
    __table_args__ = (
        Index("ix_exposure_scan_probe_started", "probe_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    probe_id: Mapped[int] = mapped_column(ForeignKey("probes.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    target_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reachable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    partial_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scanner_version: Mapped[str] = mapped_column(String(64), default="1.0", nullable=False)

class ExposureResult(Base):
    __tablename__ = "exposure_results"
    __table_args__ = (
        UniqueConstraint("scan_id", "asset_id", name="uq_exposure_scan_asset"),
        Index("ix_exposure_result_status", "status"),
        Index("ix_exposure_result_vendor_category", "vendor", "category"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("exposure_scans.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("ai_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    destination: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[Category] = mapped_column(Enum(Category), nullable=False, index=True)
    status: Mapped[ExposureStatus] = mapped_column(Enum(ExposureStatus), default=ExposureStatus.unknown, nullable=False, index=True)
    dns_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tcp_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tls_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    http_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    resolved_ip: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(String(128))
    dns_cname: Mapped[str | None] = mapped_column(String(512))
    tls_version: Mapped[str | None] = mapped_column(String(64))
    tls_cipher: Mapped[str | None] = mapped_column(String(128))
    tls_issuer: Mapped[str | None] = mapped_column(Text)
    tls_subject: Mapped[str | None] = mapped_column(Text)
    http_server: Mapped[str | None] = mapped_column(String(256))
    http_location: Mapped[str | None] = mapped_column(Text)
    http_content_type: Mapped[str | None] = mapped_column(String(256))
    redirect_chain: Mapped[str | None] = mapped_column(Text)
    exposure_confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
