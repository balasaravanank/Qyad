// Opt-in only after checking host policy. No credentials or user data needed.
export default {
  async scheduled(_event, env) {
    let url;
    try {url = new URL(env.HEALTH_URL);} catch {throw new Error('Set HEALTH_URL');}
    if(url.protocol !== 'https:' || url.pathname !== '/api/v1/health' || url.username || url.password || url.search || url.hash) throw new Error('HEALTH_URL must be the exact HTTPS health endpoint');
    const response = await fetch(url, {redirect:'error', headers:{'Cache-Control':'no-cache'}, signal:AbortSignal.timeout(20000)});
    if(!response.ok) throw new Error('Health request failed, HTTP '+response.status);
    const body=await response.json();
    if(body.ok!==true) throw new Error('Unexpected health response');
  }
};
