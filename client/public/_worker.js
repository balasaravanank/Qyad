// Same-origin API gateway. BACKEND_ORIGIN is a public HTTPS origin, not a secret.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    const json = (status, detail) => Response.json({detail}, {status, headers:{'Cache-Control':'no-store'}});
    if (!url.pathname.startsWith('/api/v1/')) return json(404, 'Use /api/v1');
    if (!env.APP_ORIGIN || url.origin !== env.APP_ORIGIN) return json(403, 'Unapproved app origin');
    const origin = request.headers.get('Origin');
    if (origin && origin !== env.APP_ORIGIN) return json(403, 'Cross-origin request blocked');
    let backend;
    try {backend = new URL(env.BACKEND_ORIGIN);} catch {return json(503, 'Backend is not configured');}
    if (backend.protocol !== 'https:' || backend.username || backend.password || backend.pathname !== '/' || backend.search || backend.hash || backend.origin === url.origin) return json(503, 'Invalid backend configuration');
    if (Number(request.headers.get('Content-Length') || 0) > 1048576) return json(413, 'Request too large');
    const target = new URL(url.pathname + url.search, backend.origin);
    const headers = new Headers(request.headers);
    for (const name of ['host','cookie','x-forwarded-host','x-forwarded-proto','x-forwarded-for','forwarded']) headers.delete(name);
    // Production uses a verified Clerk bearer token, never a local session cookie.
    try {
      const upstream = await fetch(target, {method:request.method, headers, body:['GET','HEAD'].includes(request.method)?undefined:request.body, redirect:'manual', signal:AbortSignal.timeout(20000)});
      if (upstream.status >= 300 && upstream.status < 400) return json(502, 'Unexpected backend redirect');
      const result = new Response(upstream.body, upstream);
      result.headers.delete('Set-Cookie');
      result.headers.set('Cache-Control','no-store');
      result.headers.set('X-Content-Type-Options','nosniff');
      return result;
    } catch {return json(502, 'Backend is unavailable. Try again later');}
  }
};
