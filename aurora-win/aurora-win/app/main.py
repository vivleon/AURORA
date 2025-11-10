from fastapi import FastAPI
from aurora_dashboard_api_stub import dash_router
from audit_middleware import AuditMiddleware
from event_collector import EventCollector
from consent_collector import ConsentCollector
from consent_api import consent_router
from event_sse_redis_router import sse_router as events_router
from rag_preview_router import preview_router

app = FastAPI()
app.include_router(dash_router, prefix="/dash")
app.include_router(consent_router, prefix="/consent")
app.include_router(events_router,  prefix="/events")
app.include_router(preview_router)

app.add_middleware(AuditMiddleware, log_path="data/audit.log")

collector = EventCollector("data/metrics.db")
consent   = ConsentCollector("data/metrics.db")
app.state.collector = collector
app.state.consent   = consent

@app.on_event("startup")
async def _boot():
    await collector.start()
    await consent.start()

@app.on_event("shutdown")
async def _stop():
    await consent.stop()
    await collector.stop()
