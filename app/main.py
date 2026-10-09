from pathlib import Path
import secrets

from fastapi import FastAPI, Depends, Response, HTTPException, Query, Body, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.config import settings
from app.db import get_db
from app.models import AIAsset, Action, AssetKind, Category, User, UserRole, Probe, ProbeType, ExposureScan, ExposureResult, ExposureStatus, utcnow_naive
from app.schemas import AssetCreate, AssetOut, DecisionIn, UserOut, ProbeCreate, ExposureBatchIn, PolicySimulationIn
from app.services.ingest import ingest_candidate
from app.security import hash_probe_token
from app.services.exposure import run_server_scan, exposure_targets, exposure_overview, scan_results, category_summary, vendor_summary, simulate_policy
from app.services.assessment import exposure_score, scan_history, scan_changes, probe_comparison, assessment_summary, assessment_csv, assessment_pdf
from app.services.executive import executive_overview
from app.security import authenticate, create_access_token, hash_password, COOKIE_NAME, require_viewer, require_analyst, require_admin, require_feed_token, current_user

VERSION = "1.0.1"
app = FastAPI(title="AI Enumerator", version=VERSION)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR/"static"), name="static")

@app.get("/health")
def health():
    return {"status":"ok","service":"ai-enumerator","version":VERSION}

@app.get("/")
def root():
    return RedirectResponse("/dashboard",status_code=302)

@app.get("/login",response_class=HTMLResponse)
def login_page():
    return (BASE_DIR/"static"/"login.html").read_text(encoding="utf-8")

@app.post("/auth/login")
def login(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    user=authenticate(db,username,password)
    if not user: raise HTTPException(401,"invalid credentials")
    token=create_access_token(user)
    response=RedirectResponse("/dashboard",status_code=303)
    response.set_cookie(COOKIE_NAME,token,httponly=True,secure=settings.auth_cookie_secure,samesite="strict",max_age=settings.jwt_ttl_minutes*60)
    return response

@app.post("/auth/logout")
def logout():
    response=RedirectResponse("/login",status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response

@app.get("/api/v1/auth/me",response_model=UserOut)
def me(user:User=Depends(current_user)):
    return user

@app.post("/api/v1/admin/users",response_model=UserOut,dependencies=[Depends(require_admin)])
def create_user(payload:dict=Body(...),db:Session=Depends(get_db)):
    username=str(payload.get("username") or "").strip()
    password=str(payload.get("password") or "")
    role_raw=str(payload.get("role") or "viewer")
    if not username or len(password)<12: raise HTTPException(400,"username required and password must be at least 12 characters")
    try: role=UserRole(role_raw)
    except ValueError: raise HTTPException(400,"invalid role")
    if db.scalar(select(User).where(User.username==username)): raise HTTPException(409,"user already exists")
    user=User(username=username,password_hash=hash_password(password),role=role,is_active=True)
    db.add(user);db.commit();db.refresh(user)
    return user

@app.get("/dashboard",response_class=HTMLResponse,dependencies=[Depends(require_viewer)])
def dashboard_page():
    return (BASE_DIR/"static"/"dashboard.html").read_text(encoding="utf-8")

@app.get("/api/v1/executive/overview",dependencies=[Depends(require_viewer)])
def executive_overview_api(db:Session=Depends(get_db)):
    return executive_overview(db)

@app.get("/intelligence",response_class=HTMLResponse,dependencies=[Depends(require_analyst)])
def intelligence_page():
    return (BASE_DIR/"static"/"intelligence.html").read_text(encoding="utf-8")

@app.get("/api/v1/assets",response_model=list[AssetOut],dependencies=[Depends(require_viewer)])
def list_assets(action:Action|None=None,category:Category|None=None,vendor:str|None=None,min_confidence:int=Query(0,ge=0,le=100),db:Session=Depends(get_db)):
    stmt=select(AIAsset).options(selectinload(AIAsset.observations))
    if action: stmt=stmt.where(AIAsset.action==action)
    if category: stmt=stmt.where(AIAsset.category==category)
    if vendor: stmt=stmt.where(AIAsset.vendor==vendor)
    stmt=stmt.where(AIAsset.confidence>=min_confidence)
    return list(db.scalars(stmt.order_by(AIAsset.confidence.desc(),AIAsset.vendor,AIAsset.value)).unique())

@app.get("/api/v1/assets/{asset_id}",response_model=AssetOut,dependencies=[Depends(require_viewer)])
def get_asset(asset_id:int,db:Session=Depends(get_db)):
    asset=db.scalar(select(AIAsset).options(selectinload(AIAsset.observations)).where(AIAsset.id==asset_id))
    if not asset: raise HTTPException(404,"asset not found")
    return asset

@app.post("/api/v1/assets",response_model=AssetOut,status_code=201,dependencies=[Depends(require_analyst)])
def create_asset(asset:AssetCreate,db:Session=Depends(get_db)):
    obj=ingest_candidate(db,kind=asset.kind,value=asset.value,vendor=asset.vendor,category=asset.category,source_type=asset.source_type,source_ref=asset.source_ref,source_confidence=asset.source_confidence,evidence=asset.evidence)
    return db.scalar(select(AIAsset).options(selectinload(AIAsset.observations)).where(AIAsset.id==obj.id))

@app.patch("/api/v1/assets/{asset_id}/decision",response_model=AssetOut,dependencies=[Depends(require_analyst)])
def decide_asset(asset_id:int,decision:DecisionIn,db:Session=Depends(get_db)):
    asset=db.scalar(select(AIAsset).options(selectinload(AIAsset.observations)).where(AIAsset.id==asset_id))
    if not asset: raise HTTPException(404,"asset not found")
    asset.action=decision.action;asset.analyst_note=decision.analyst_note
    asset.approved=decision.action in {Action.block,Action.allow,Action.monitor}
    if decision.action in {Action.review,Action.ignore}: asset.approved=False
    db.commit();db.refresh(asset)
    return asset

def _feed_assets(db,action,kinds=None,categories=None):
    stmt=select(AIAsset).where(AIAsset.action==action,AIAsset.approved.is_(True))
    if kinds: stmt=stmt.where(AIAsset.kind.in_(kinds))
    if categories: stmt=stmt.where(AIAsset.category.in_(categories))
    return list(db.scalars(stmt.order_by(AIAsset.value)))

def _plain(values):
    values=sorted(set(v.strip().lower() for v in values if v.strip()))
    return Response("\n".join(values)+("\n" if values else ""),media_type="text/plain")

@app.get("/feeds/block-all.txt",dependencies=[Depends(require_feed_token)])
def block_all_feed(db:Session=Depends(get_db)):
    return _plain([x.value for x in _feed_assets(db,Action.block)])

@app.get("/feeds/genai-web.txt",dependencies=[Depends(require_feed_token)])
def genai_web_feed(db:Session=Depends(get_db)):
    return _plain([x.value for x in _feed_assets(db,Action.block,categories=[Category.genai_web,Category.ai_coding])])

@app.get("/feeds/ai-api.txt",dependencies=[Depends(require_feed_token)])
def ai_api_feed(db:Session=Depends(get_db)):
    return _plain([x.value for x in _feed_assets(db,Action.block,categories=[Category.ai_api])])

@app.get("/feeds/model-distribution.txt",dependencies=[Depends(require_feed_token)])
def model_distribution_feed(db:Session=Depends(get_db)):
    return _plain([x.value for x in _feed_assets(db,Action.block,categories=[Category.model_registry,Category.model_cdn,Category.llm_runtime])])

@app.get("/feeds/allow.txt",dependencies=[Depends(require_feed_token)])
def allow_feed(db:Session=Depends(get_db)):
    return _plain([x.value for x in _feed_assets(db,Action.allow)])

@app.get("/exposure", response_class=HTMLResponse, dependencies=[Depends(require_viewer)])
def exposure_page():
    return (BASE_DIR/"static"/"exposure.html").read_text(encoding="utf-8")

@app.get("/api/v1/exposure/overview", dependencies=[Depends(require_viewer)])
def exposure_overview_api(db:Session=Depends(get_db)):
    return exposure_overview(db)

@app.post("/api/v1/exposure/scan/server", dependencies=[Depends(require_analyst)])
async def exposure_server_scan(db:Session=Depends(get_db)):
    scan=await run_server_scan(db)
    return {"scan_id":scan.id,"targets":scan.target_count,"reachable":scan.reachable_count,"blocked":scan.blocked_count,"partial":scan.partial_count,"failed":scan.failed_count}

@app.get("/api/v1/exposure/scans/{scan_id}/results", dependencies=[Depends(require_viewer)])
def exposure_results_api(scan_id:int, db:Session=Depends(get_db)):
    rows=scan_results(db,scan_id)
    return [{"id":r.id,"destination":r.destination,"vendor":r.vendor,"category":r.category.value,
        "status":r.status.value,"dns_ok":r.dns_ok,"tcp_ok":r.tcp_ok,"tls_ok":r.tls_ok,
        "http_ok":r.http_ok,"http_status":r.http_status,"latency_ms":r.latency_ms,
        "resolved_ip":r.resolved_ip,"error":r.error,"failure_reason":r.failure_reason,
        "dns_cname":r.dns_cname,"tls_version":r.tls_version,"tls_cipher":r.tls_cipher,
        "tls_issuer":r.tls_issuer,"tls_subject":r.tls_subject,"http_server":r.http_server,
        "http_location":r.http_location,"http_content_type":r.http_content_type,
        "redirect_chain":r.redirect_chain,"exposure_confidence":r.exposure_confidence} for r in rows]

@app.get("/api/v1/exposure/scans/{scan_id}/categories", dependencies=[Depends(require_viewer)])
def exposure_categories_api(scan_id:int, db:Session=Depends(get_db)):
    return category_summary(db,scan_id)

@app.get("/api/v1/exposure/scans/{scan_id}/vendors", dependencies=[Depends(require_viewer)])
def exposure_vendors_api(scan_id:int, db:Session=Depends(get_db)):
    return vendor_summary(db,scan_id)

@app.post("/api/v1/exposure/policy-simulation", dependencies=[Depends(require_analyst)])
def exposure_policy_simulation(payload:PolicySimulationIn, db:Session=Depends(get_db)):
    return simulate_policy(db,payload.category_actions)

@app.post("/api/v1/probes", dependencies=[Depends(require_admin)])
def create_probe(payload:ProbeCreate, db:Session=Depends(get_db)):
    if db.scalar(select(Probe).where(Probe.name==payload.name)): raise HTTPException(409,"probe already exists")
    token=secrets.token_urlsafe(32)
    probe=Probe(name=payload.name.strip(),probe_type=ProbeType.agent,network_label=payload.network_label,
                description=payload.description,token_hash=hash_probe_token(token),is_active=True)
    db.add(probe);db.commit();db.refresh(probe)
    return {"id":probe.id,"name":probe.name,"network_label":probe.network_label,"token":token}

def _probe_auth(x_probe_token:str|None, db:Session):
    if not x_probe_token: raise HTTPException(401,"missing probe token")
    probe=db.scalar(select(Probe).where(Probe.token_hash==hash_probe_token(x_probe_token),Probe.is_active.is_(True)))
    if not probe: raise HTTPException(401,"invalid probe token")
    return probe

@app.get("/api/v1/probe/targets")
def probe_targets_api(x_probe_token:str|None=Header(default=None), db:Session=Depends(get_db)):
    probe=_probe_auth(x_probe_token,db);probe.last_seen_at=utcnow_naive();db.commit()
    return [{"asset_id":a.id,"destination":a.value,"vendor":a.vendor,"category":a.category.value} for a in exposure_targets(db)]

@app.post("/api/v1/probe/results")
def probe_results_api(payload:ExposureBatchIn, x_probe_token:str|None=Header(default=None), db:Session=Depends(get_db)):
    probe=_probe_auth(x_probe_token,db)
    scan=ExposureScan(probe_id=probe.id,started_at=payload.scan_started_at.replace(tzinfo=None),
                      finished_at=payload.scan_finished_at.replace(tzinfo=None),target_count=len(payload.results),
                      scanner_version=payload.scanner_version)
    db.add(scan);db.flush();counters={x.value:0 for x in ExposureStatus};accepted=0
    for item in payload.results:
        asset=db.scalar(select(AIAsset).where(AIAsset.id==item.asset_id))
        if not asset: continue
        try: status=ExposureStatus(item.status)
        except ValueError: status=ExposureStatus.unknown
        counters[status.value]+=1
        db.add(ExposureResult(scan_id=scan.id,asset_id=asset.id,checked_at=utcnow_naive(),destination=asset.value,
            vendor=asset.vendor,category=asset.category,status=status,dns_ok=item.dns_ok,tcp_ok=item.tcp_ok,
            tls_ok=item.tls_ok,http_ok=item.http_ok,http_status=item.http_status,latency_ms=item.latency_ms,
            resolved_ip=item.resolved_ip,error=item.error))
        accepted+=1
    scan.reachable_count=counters["reachable"];scan.blocked_count=counters["blocked"]
    scan.partial_count=counters["partial"];scan.failed_count=counters["failed"];probe.last_seen_at=utcnow_naive()
    db.commit();db.refresh(scan)
    return {"scan_id":scan.id,"accepted":accepted,"reachable":scan.reachable_count,"blocked":scan.blocked_count,"partial":scan.partial_count,"failed":scan.failed_count}

@app.get("/api/v1/probes", dependencies=[Depends(require_viewer)])
def list_probes(db:Session=Depends(get_db)):
    probes=list(db.scalars(select(Probe).order_by(Probe.name)))
    return [{"id":p.id,"name":p.name,"type":p.probe_type.value,"network_label":p.network_label,
             "last_seen_at":p.last_seen_at.isoformat() if p.last_seen_at else None,"active":p.is_active} for p in probes]

@app.get("/assessment", response_class=HTMLResponse, dependencies=[Depends(require_viewer)])
def assessment_page():
    return (BASE_DIR/"static"/"assessment.html").read_text(encoding="utf-8")

@app.get("/api/v1/assessment/summary", dependencies=[Depends(require_viewer)])
def assessment_summary_api(probe_id:int|None=None, db:Session=Depends(get_db)):
    return assessment_summary(db, probe_id)

@app.get("/api/v1/assessment/score/{scan_id}", dependencies=[Depends(require_viewer)])
def assessment_score_api(scan_id:int, db:Session=Depends(get_db)):
    return exposure_score(db, scan_id)

@app.get("/api/v1/assessment/history/{probe_id}", dependencies=[Depends(require_viewer)])
def assessment_history_api(probe_id:int, limit:int=Query(30,ge=1,le=365), db:Session=Depends(get_db)):
    return scan_history(db, probe_id, limit)

@app.get("/api/v1/assessment/changes/{probe_id}", dependencies=[Depends(require_viewer)])
def assessment_changes_api(probe_id:int, db:Session=Depends(get_db)):
    return scan_changes(db, probe_id)

@app.get("/api/v1/assessment/comparison", dependencies=[Depends(require_viewer)])
def assessment_comparison_api(db:Session=Depends(get_db)):
    return probe_comparison(db)

@app.get("/api/v1/assessment/report.csv", dependencies=[Depends(require_viewer)])
def assessment_csv_api(probe_id:int|None=None, db:Session=Depends(get_db)):
    content=assessment_csv(db,probe_id)
    if not content: raise HTTPException(404,"no assessment data available")
    return Response(content=content,media_type="text/csv; charset=utf-8",headers={"Content-Disposition":'attachment; filename="ai-egress-exposure-assessment.csv"'})

@app.get("/api/v1/assessment/report.pdf", dependencies=[Depends(require_viewer)])
def assessment_pdf_api(probe_id:int|None=None, db:Session=Depends(get_db)):
    content=assessment_pdf(db,probe_id)
    if not content: raise HTTPException(404,"no assessment data available")
    return Response(content=content,media_type="application/pdf",headers={"Content-Disposition":'attachment; filename="ai-egress-exposure-assessment.pdf"'})

@app.get("/api/v1/exposure/specialized", dependencies=[Depends(require_viewer)])
def exposure_specialized_api(db:Session=Depends(get_db)):
    from app.services.exposure import latest_scan, scan_results
    scan=latest_scan(db)
    if not scan: return {"scan_id":None,"ai_api":{"total":0,"exposed":0},"model_distribution":{"total":0,"exposed":0}}
    rows=scan_results(db,scan.id)
    api=[r for r in rows if r.category==Category.ai_api]
    model=[r for r in rows if r.category in {Category.model_registry,Category.model_cdn,Category.llm_runtime}]
    exposed=lambda rows:sum(1 for r in rows if r.status in {ExposureStatus.reachable,ExposureStatus.partial})
    return {"scan_id":scan.id,"ai_api":{"total":len(api),"exposed":exposed(api)},
            "model_distribution":{"total":len(model),"exposed":exposed(model)}}
