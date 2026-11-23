import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from urllib.parse import urlparse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, engine, get_db
from .deps import current_user
from fastapi import Depends
from .routers import auth, spaces, items, opportunities, applications, updates, today, agent, audit, discovery

AUTH_MODE = os.getenv('AUTH_MODE', 'clerk' if os.getenv('APP_ENV') == 'production' else 'local')
if AUTH_MODE not in ('clerk', 'local'):
    raise RuntimeError('AUTH_MODE must be clerk or local')
if os.getenv('APP_ENV') == 'production':
    from .clerk_auth import settings
    if AUTH_MODE != 'clerk' or not settings()[-1]:
        raise RuntimeError('Production requires configured Clerk authentication')
    if not os.getenv('PUBLIC_URL', '').startswith('https://'):
        raise RuntimeError('Production requires an HTTPS PUBLIC_URL')
PRODUCTION = os.getenv('APP_ENV', 'development') == 'production'
app = FastAPI(title="Qyad", version="0.9.2", docs_url=None if PRODUCTION else "/docs", redoc_url=None if PRODUCTION else "/redoc", openapi_url=None if PRODUCTION else "/openapi.json")
allowed_hosts = [v.strip() for v in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if v.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
if PRODUCTION:
    from .limits import RequestLimits
    app.add_middleware(RequestLimits)

@app.middleware('http')
async def safety_headers(request: Request, call_next):
    # Reject browser cross-origin writes. Non-browser agent tokens remain supported.
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin:
        expected = os.getenv('PUBLIC_URL', '').rstrip('/') or str(request.base_url).rstrip('/')
        if origin.rstrip('/') != expected:
            return JSONResponse({'detail': 'Cross-origin writes are not allowed'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    if PRODUCTION:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

# MVP: create_all instead of migrations (see docs/gap-analysis.md G-T6).
Base.metadata.create_all(bind=engine)

for router_module in (auth, spaces, items, opportunities, applications, updates, today, agent, audit, discovery):
    for route in router_module.router.routes:
        kwargs = dict(methods=list(route.methods), status_code=route.status_code,
                      response_model=route.response_model, name=route.name)
        v1_path=route.path.replace('/api/', '/api/v1/', 1)
        if '/discover' in v1_path:
            v1_path=v1_path.replace('/discover', '/opportunity-catalog')
            if route.path=='/api/discover':
                # v1 catalog is editorial data, not the removed global discovery feed.
                def catalog(user=Depends(current_user), db=Depends(get_db)):
                    return discovery.discover(source='curated', user=user, db=db)
                app.add_api_route(v1_path,catalog,methods=['GET'],name='opportunity_catalog')
                if not PRODUCTION and os.getenv('ENABLE_LEGACY_API')=='1':
                    app.add_api_route(route.path,route.endpoint,include_in_schema=False,**kwargs)
                continue
        if route.path=='/api/discover/{job_id}/save':
            def catalog_save(job_id: str, data: discovery.SaveIn, user=Depends(current_user), db=Depends(get_db)):
                from fastapi import HTTPException
                if not any(j['id']==job_id for j in discovery.curated_jobs()):
                    raise HTTPException(404, 'Listing is not in the current catalog')
                return discovery.save_job(job_id,data,user,db)
            app.add_api_route(v1_path,catalog_save,methods=['POST'],name='save_catalog_opportunity')
        else:
            app.add_api_route(v1_path, route.endpoint, **kwargs)
        if not PRODUCTION and os.getenv('ENABLE_LEGACY_API')=='1':
            app.add_api_route(route.path, route.endpoint, include_in_schema=False, **kwargs)

STATIC_DIR = Path(__file__).resolve().parents[2] / "client" / "public"


@app.get("/", include_in_schema=False)
def index():
    if PRODUCTION:
        from fastapi import HTTPException
        raise HTTPException(404, 'Frontend is hosted separately')
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR / "static", check_dir=False), name="static")


@app.get("/api/v1/health")
def health():
    return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})

if not PRODUCTION and os.getenv('ENABLE_LEGACY_API')=='1':
    app.add_api_route('/api/health', health, methods=['GET'], include_in_schema=False)
