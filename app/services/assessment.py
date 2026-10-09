from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO, StringIO
import csv

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Probe, ExposureScan, ExposureResult, ExposureStatus, Category

CATEGORY_WEIGHTS = {
    Category.model_registry: 18,
    Category.model_cdn: 18,
    Category.llm_runtime: 16,
    Category.ai_api: 14,
    Category.ai_coding: 10,
    Category.genai_web: 8,
    Category.enterprise_approved: 2,
}

STATUS_FACTOR = {
    ExposureStatus.reachable: 1.0,
    ExposureStatus.partial: 0.5,
    ExposureStatus.blocked: 0.0,
    ExposureStatus.failed: 0.0,
    ExposureStatus.unknown: 0.0,
}

def _latest_scan_for_probe(db: Session, probe_id: int) -> ExposureScan | None:
    return db.scalar(
        select(ExposureScan).where(ExposureScan.probe_id == probe_id)
        .order_by(ExposureScan.started_at.desc()).limit(1)
    )

def _latest_scans_by_probe(db: Session) -> list[tuple[Probe, ExposureScan]]:
    probes = list(db.scalars(select(Probe).where(Probe.is_active.is_(True)).order_by(Probe.name)))
    out = []
    for probe in probes:
        scan = _latest_scan_for_probe(db, probe.id)
        if scan:
            out.append((probe, scan))
    return out

def _scan_results(db: Session, scan_id: int) -> list[ExposureResult]:
    return list(db.scalars(
        select(ExposureResult).where(ExposureResult.scan_id == scan_id)
        .order_by(ExposureResult.vendor, ExposureResult.category, ExposureResult.destination)
    ))

def exposure_score(db: Session, scan_id: int) -> dict:
    rows = _scan_results(db, scan_id)
    by_category = defaultdict(list)
    for row in rows:
        by_category[row.category].append(row)

    weighted = 0.0
    weight_total = 0.0
    detail = []
    for category, items in sorted(by_category.items(), key=lambda x: x[0].value):
        weight = CATEGORY_WEIGHTS.get(category, 5)
        exposure_units = sum(STATUS_FACTOR.get(x.status, 0.0) for x in items)
        rate = exposure_units / len(items) if items else 0.0
        weighted += rate * weight
        weight_total += weight
        detail.append({
            "category": category.value,
            "weight": weight,
            "targets": len(items),
            "reachable": sum(1 for x in items if x.status == ExposureStatus.reachable),
            "partial": sum(1 for x in items if x.status == ExposureStatus.partial),
            "exposure_rate": round(rate * 100, 1),
        })

    score = round((weighted / weight_total) * 100) if weight_total else 0
    band = "high" if score >= 75 else "elevated" if score >= 50 else "moderate" if score >= 25 else "low"
    return {
        "scan_id": scan_id,
        "score": score,
        "band": band,
        "methodology": "Weighted reachability: reachable=1.0, partial=0.5, blocked/failed=0. Category weights emphasize model distribution, runtimes and AI APIs.",
        "categories": detail,
    }

def scan_history(db: Session, probe_id: int, limit: int = 30) -> list[dict]:
    rows = list(db.scalars(
        select(ExposureScan).where(ExposureScan.probe_id == probe_id)
        .order_by(ExposureScan.started_at.desc()).limit(limit)
    ))
    return [{
        "scan_id": s.id,
        "started_at": s.started_at.isoformat(),
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "targets": s.target_count,
        "reachable": s.reachable_count,
        "partial": s.partial_count,
        "blocked": s.blocked_count,
        "failed": s.failed_count,
        "score": exposure_score(db, s.id)["score"],
    } for s in rows]

def scan_changes(db: Session, probe_id: int) -> dict:
    scans = list(db.scalars(
        select(ExposureScan).where(ExposureScan.probe_id == probe_id)
        .order_by(ExposureScan.started_at.desc()).limit(2)
    ))
    if not scans:
        return {"probe_id": probe_id, "current_scan_id": None, "previous_scan_id": None, "changes": []}
    current = scans[0]
    if len(scans) == 1:
        return {"probe_id": probe_id, "current_scan_id": current.id, "previous_scan_id": None, "changes": []}
    previous = scans[1]
    cur = {r.asset_id: r for r in _scan_results(db, current.id)}
    old = {r.asset_id: r for r in _scan_results(db, previous.id)}
    changes = []
    for asset_id in sorted(set(cur) | set(old)):
        a = old.get(asset_id); b = cur.get(asset_id)
        if a is None and b is not None:
            changes.append({"destination": b.destination, "vendor": b.vendor, "category": b.category.value, "from_status": None, "to_status": b.status.value, "change": "new_target"})
        elif a is not None and b is None:
            changes.append({"destination": a.destination, "vendor": a.vendor, "category": a.category.value, "from_status": a.status.value, "to_status": None, "change": "removed_target"})
        elif a and b and a.status != b.status:
            if b.status in {ExposureStatus.reachable, ExposureStatus.partial} and a.status not in {ExposureStatus.reachable, ExposureStatus.partial}:
                kind = "became_reachable"
            elif a.status in {ExposureStatus.reachable, ExposureStatus.partial} and b.status not in {ExposureStatus.reachable, ExposureStatus.partial}:
                kind = "became_unreachable"
            else:
                kind = "status_changed"
            changes.append({"destination": b.destination, "vendor": b.vendor, "category": b.category.value, "from_status": a.status.value, "to_status": b.status.value, "change": kind})
    return {
        "probe_id": probe_id,
        "current_scan_id": current.id,
        "previous_scan_id": previous.id,
        "current_started_at": current.started_at.isoformat(),
        "previous_started_at": previous.started_at.isoformat(),
        "changes": changes,
    }

def probe_comparison(db: Session) -> dict:
    latest = _latest_scans_by_probe(db)
    probes = []
    all_assets = set()
    result_maps = {}
    for probe, scan in latest:
        rows = _scan_results(db, scan.id)
        result_maps[probe.id] = {r.destination: r for r in rows}
        all_assets.update(r.destination for r in rows)
        score = exposure_score(db, scan.id)
        probes.append({
            "probe_id": probe.id, "probe": probe.name, "network_label": probe.network_label,
            "scan_id": scan.id, "started_at": scan.started_at.isoformat(), "score": score["score"],
            "reachable": scan.reachable_count, "partial": scan.partial_count,
            "blocked": scan.blocked_count, "failed": scan.failed_count,
        })
    matrix = []
    for destination in sorted(all_assets):
        first = next((m[destination] for m in result_maps.values() if destination in m), None)
        row = {"destination": destination, "vendor": first.vendor if first else None,
               "category": first.category.value if first else None, "probes": {}}
        for probe in probes:
            result = result_maps.get(probe["probe_id"], {}).get(destination)
            row["probes"][str(probe["probe_id"])] = result.status.value if result else "not_tested"
        matrix.append(row)
    return {"probes": probes, "matrix": matrix}

def assessment_summary(db: Session, probe_id: int | None = None) -> dict:
    if probe_id is None:
        pair = _latest_scans_by_probe(db)
        if not pair: return {"available": False}
        probe, scan = pair[0]
    else:
        probe = db.get(Probe, probe_id)
        if not probe: return {"available": False}
        scan = _latest_scan_for_probe(db, probe.id)
        if not scan: return {"available": False}

    rows = _scan_results(db, scan.id)
    score = exposure_score(db, scan.id)
    changes = scan_changes(db, probe.id)
    by_vendor = defaultdict(lambda: {"total": 0, "reachable": 0, "partial": 0})
    by_category = defaultdict(lambda: {"total": 0, "reachable": 0, "partial": 0})
    for r in rows:
        v = by_vendor[r.vendor]; v["total"] += 1
        if r.status == ExposureStatus.reachable: v["reachable"] += 1
        if r.status == ExposureStatus.partial: v["partial"] += 1
        c = by_category[r.category.value]; c["total"] += 1
        if r.status == ExposureStatus.reachable: c["reachable"] += 1
        if r.status == ExposureStatus.partial: c["partial"] += 1

    exposed = [r for r in rows if r.status in {ExposureStatus.reachable, ExposureStatus.partial}]
    model_services = [r for r in exposed if r.category in {Category.model_registry, Category.model_cdn, Category.llm_runtime}]
    api_services = [r for r in exposed if r.category == Category.ai_api]
    return {
        "available": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": {"id": probe.id, "name": probe.name, "network_label": probe.network_label},
        "scan": {"id": scan.id, "started_at": scan.started_at.isoformat(),
                 "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
                 "targets": scan.target_count, "reachable": scan.reachable_count,
                 "partial": scan.partial_count, "blocked": scan.blocked_count, "failed": scan.failed_count},
        "score": score,
        "reachable_model_distribution": len(model_services),
        "reachable_ai_apis": len(api_services),
        "vendors": [{"vendor": k, **v} for k, v in sorted(by_vendor.items())],
        "categories": [{"category": k, **v} for k, v in sorted(by_category.items())],
        "changes": changes["changes"],
        "limitations": [
            "Reachability demonstrates egress exposure from the selected probe location; it is not proof of end-user activity.",
            "HTTP/TLS behavior can be affected by proxies, inspection layers, DNS policy and vendor edge controls.",
            "A reachable endpoint confirms network path and service response, not authenticated application functionality."
        ],
        "next_phase": [
            "Review high-confidence exposed AI API and model-distribution endpoints.",
            "Apply or adjust egress controls according to organizational policy and repeat the assessment.",
            "Deploy additional probes in relevant network segments to compare exposure posture."
        ]
    }

def assessment_csv(db: Session, probe_id: int | None = None) -> bytes:
    summary = assessment_summary(db, probe_id)
    if not summary.get("available"): return b""
    rows = _scan_results(db, summary["scan"]["id"])
    buf = StringIO(); w = csv.writer(buf)
    w.writerow(["destination","vendor","category","status","dns_ok","tcp_ok","tls_ok","http_ok","http_status","latency_ms","resolved_ip","error"])
    for r in rows:
        w.writerow([r.destination,r.vendor,r.category.value,r.status.value,r.dns_ok,r.tcp_ok,r.tls_ok,r.http_ok,r.http_status,r.latency_ms,r.resolved_ip,r.error])
    return buf.getvalue().encode("utf-8-sig")

def assessment_pdf(db: Session, probe_id: int | None = None) -> bytes:
    summary = assessment_summary(db, probe_id)
    if not summary.get("available"): return b""

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=16*mm, bottomMargin=16*mm,
                            title=settings.assessment_report_title, author="AI Enumerator")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#5b6770")))
    story = [
        Paragraph(settings.assessment_report_title, styles["Title"]),
        Paragraph(f"{settings.assessment_company_name} - Probe: {summary['probe']['name']} ({summary['probe']['network_label'] or 'unlabeled network'})", styles["SmallMuted"]),
        Spacer(1, 8*mm)
    ]
    metrics = [
        ["Exposure Score","Targets","Reachable/Partial","Model Distribution","AI APIs"],
        [f"{summary['score']['score']}/100", str(summary["scan"]["targets"]),
         str(summary["scan"]["reachable"]+summary["scan"]["partial"]),
         str(summary["reachable_model_distribution"]), str(summary["reachable_ai_apis"])]
    ]
    t=Table(metrics,colWidths=[34*mm]*5)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#10202c")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("FONTSIZE",(0,1),(-1,1),14),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#c7d1d8")),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)
    ]))
    story += [t, Spacer(1,8*mm), Paragraph("Executive Summary",styles["Heading1"])]
    exposed=summary["scan"]["reachable"]+summary["scan"]["partial"]
    story.append(Paragraph(
        f"The assessment tested {summary['scan']['targets']} GenAI-related endpoints from the selected network. "
        f"{exposed} demonstrated complete or partial egress reachability. The AI Egress Exposure Score is "
        f"{summary['score']['score']}/100 ({summary['score']['band']}). This demonstrates network exposure only; it does not establish employee usage.",
        styles["BodyText"]))
    story += [Spacer(1,5*mm),Paragraph("Exposure by Category",styles["Heading1"])]
    data=[["Category","Targets","Reachable","Partial"]]+[[r["category"],r["total"],r["reachable"],r["partial"]] for r in summary["categories"]]
    t=Table(data,colWidths=[65*mm,30*mm,30*mm,30*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e7eef2")),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                           ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#c1ccd3")),("FONTSIZE",(0,0),(-1,-1),8.5),
                           ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [t,Spacer(1,6*mm),Paragraph("Notable Changes Since Previous Scan",styles["Heading1"])]
    if summary["changes"]:
        for c in summary["changes"][:20]:
            story.append(Paragraph(f"- {c['destination']} ({c['vendor']} / {c['category']}): {c['from_status'] or 'new'} -> {c['to_status'] or 'removed'} [{c['change']}]",styles["BodyText"]))
    else:
        story.append(Paragraph("No status changes were detected, or no previous scan is available.",styles["BodyText"]))
    story += [Spacer(1,5*mm),Paragraph("Interpretation and Limitations",styles["Heading1"])]
    for item in summary["limitations"]: story.append(Paragraph(f"- {item}",styles["BodyText"]))
    story.append(Paragraph("Recommended Next Phase",styles["Heading1"]))
    for item in summary["next_phase"]: story.append(Paragraph(f"- {item}",styles["BodyText"]))
    story += [Spacer(1,6*mm),Paragraph(f"Scoring methodology: {summary['score']['methodology']}",styles["SmallMuted"])]
    doc.build(story)
    return buf.getvalue()
