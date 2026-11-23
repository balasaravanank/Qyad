"""Single-process rate limit. Deploy one worker; not a distributed abuse service."""
import time, threading
from collections import OrderedDict
from starlette.responses import JSONResponse
class RequestLimits:
    def __init__(self, app):
        self.app=app; self.buckets=OrderedDict(); self.lock=threading.Lock()
    async def __call__(self, scope, receive, send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        path=scope['path']
        if not path.startswith('/api/'):return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]))
        try: size=int(headers.get(b'content-length',b'0'))
        except ValueError:size=4000000
        if size>3000000:return await JSONResponse({'detail':'Request too large'},413)(scope,receive,send)
        # Trusted proxy populates scope.client. No client-supplied forwarded header is read here.
        ip=(scope.get('client') or ('unknown',))[0]
        limit=15 if '/auth/' in path or path.endswith('/resume-preview') else 180
        key=(ip, 'sensitive' if limit==15 else 'api'); now=time.monotonic()
        with self.lock:
            count,started=self.buckets.pop(key,(0,now))
            if now-started>=60:count,started=0,now
            self.buckets[key]=(count+1,started)
            while len(self.buckets)>10000:self.buckets.popitem(last=False)
        if count>=limit:
            return await JSONResponse({'detail':'Too many requests. Try again in a minute'},429,headers={'Retry-After':'60','Cache-Control':'no-store'})(scope,receive,send)
        await self.app(scope,receive,send)
