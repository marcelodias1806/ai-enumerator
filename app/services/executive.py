from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import AIAsset, Action, ExposureStatus, SourceType
from app.services.exposure import latest_scan, scan_results
from app.services.assessment import exposure_score

def executive_overview(db: Session) -> dict:
    scan=latest_scan(db)
    asset_count=db.scalar(select(func.count(AIAsset.id))) or 0
    vendor_count=db.scalar(select(func.count(func.distinct(AIAsset.vendor)))) or 0
    high_conf=db.scalar(select(func.count(AIAsset.id)).where(AIAsset.confidence>=80)) or 0
    review_count=db.scalar(select(func.count(AIAsset.id)).where(AIAsset.action==Action.review)) or 0
    if not scan:
        return {"version":"1.0.1","exposure_live":False,"intelligence_live":asset_count>0,"scan":None,
                "intelligence":{"assets":asset_count,"vendors":vendor_count,"high_confidence":high_conf,"review_queue":review_count},
                "categories":[],"vendors":[],"findings":[]}
    rows=scan_results(db,scan.id)
    score=exposure_score(db,scan.id)
    exposed=[r for r in rows if r.status in {ExposureStatus.reachable,ExposureStatus.partial}]
    api_http=sum(1 for r in rows if r.category.value=="ai_api" and r.status==ExposureStatus.reachable)
    api_exposed=sum(1 for r in rows if r.category.value=="ai_api" and r.status in {ExposureStatus.reachable,ExposureStatus.partial})
    model_exposed=sum(1 for r in rows if r.category.value in {"model_registry","model_cdn","llm_runtime"} and r.status in {ExposureStatus.reachable,ExposureStatus.partial})
    cats=defaultdict(lambda:{"total":0,"exposed":0})
    vendors=defaultdict(lambda:{"total":0,"reachable":0,"partial":0})
    for r in rows:
        cats[r.category.value]["total"]+=1
        vendors[r.vendor]["total"]+=1
        if r.status in {ExposureStatus.reachable,ExposureStatus.partial}: cats[r.category.value]["exposed"]+=1
        if r.status==ExposureStatus.reachable: vendors[r.vendor]["reachable"]+=1
        if r.status==ExposureStatus.partial: vendors[r.vendor]["partial"]+=1
    vendor_rows=[]
    for name,v in vendors.items():
        v["vendor"]=name;v["exposed"]=v["reachable"]+v["partial"]
        v["exposure_pct"]=round((v["exposed"]/v["total"])*100) if v["total"] else 0
        vendor_rows.append(v)
    vendor_rows.sort(key=lambda x:(x["exposed"],x["exposure_pct"]),reverse=True)
    findings=[]
    if api_exposed: findings.append({"title":"AI API exposure","detail":f"{api_exposed} API endpoints are reachable or partially reachable","severity":"high"})
    if model_exposed: findings.append({"title":"Model distribution exposure","detail":f"{model_exposed} registry/CDN/runtime endpoints are reachable or partial","severity":"high"})
    for v in vendor_rows[:3]:
        if v["exposure_pct"]>=80 and v["total"]>=2: findings.append({"title":v["vendor"],"detail":f"{v['exposed']}/{v['total']} catalog endpoints exposed","severity":"high" if v["exposure_pct"]==100 else "medium"})
    return {"version":"1.0.1","exposure_live":True,"intelligence_live":asset_count>0,
            "scan":{"id":scan.id,"last_scan":scan.finished_at.isoformat() if scan.finished_at else scan.started_at.isoformat(),
                    "targets":scan.target_count,"reachable":scan.reachable_count,"partial":scan.partial_count,
                    "blocked":scan.blocked_count,"failed":scan.failed_count,"exposed":len(exposed),
                    "ai_api_reachable":api_http,"ai_api_exposed":api_exposed,"model_distribution_exposed":model_exposed},
            "score":score,"intelligence":{"assets":asset_count,"vendors":vendor_count,"high_confidence":high_conf,"review_queue":review_count},
            "categories":[{"category":k,**v} for k,v in sorted(cats.items(),key=lambda x:x[1]["total"],reverse=True)],
            "vendors":vendor_rows[:10],"findings":findings[:5]}
