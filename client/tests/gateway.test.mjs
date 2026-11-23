import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../public/_worker.js';
const env={APP_ORIGIN:'https://app.example.com',BACKEND_ORIGIN:'https://api.example.com',ASSETS:{fetch:()=>new Response('asset')}};
test('static assets bypass API',async()=>assert.equal(await (await worker.fetch(new Request('https://app.example.com/'),env)).text(),'asset'));
test('unversioned and wrong origin blocked',async()=>{
 assert.equal((await worker.fetch(new Request('https://app.example.com/api/spaces'),env)).status,404);
 assert.equal((await worker.fetch(new Request('https://preview.example.com/api/v1/spaces'),env)).status,403);
 assert.equal((await worker.fetch(new Request('https://app.example.com/api/v1/spaces',{headers:{Origin:'https://evil.example'}}),env)).status,403);
});
test('proxy only fixed HTTPS backend, forwards bearer, strips cookies and disables cache',async()=>{
 const prior=global.fetch;let called;
 global.fetch=async(url,opts)=>{called={url:String(url),opts};return new Response('{}',{headers:{'Set-Cookie':'bad=1','Cache-Control':'public'}});};
 try{const res=await worker.fetch(new Request('https://app.example.com/api/v1/spaces?q=1',{headers:{Authorization:'Bearer synthetic',Cookie:'ws_session=old'}}),env);
 assert.equal(called.url,'https://api.example.com/api/v1/spaces?q=1');assert.equal(called.opts.headers.get('authorization'),'Bearer synthetic');assert.equal(called.opts.headers.get('cookie'),null);assert.equal(res.headers.get('set-cookie'),null);assert.equal(res.headers.get('cache-control'),'no-store');
 assert.equal((await worker.fetch(new Request('https://app.example.com/api/v1/spaces'),{...env,BACKEND_ORIGIN:'http://localhost:8000'})).status,503);
 }finally{global.fetch=prior;}
});
test('upstream errors and redirects fail safely',async()=>{
 const prior=global.fetch;
 try {global.fetch=async()=>new Response(null,{status:302,headers:{Location:'https://elsewhere.example'}});assert.equal((await worker.fetch(new Request('https://app.example.com/api/v1/spaces'),env)).status,502);
 global.fetch=async()=>{throw new Error('private internal detail')};const r=await worker.fetch(new Request('https://app.example.com/api/v1/spaces'),env);assert.equal(r.status,502);assert.equal((await r.text()).includes('private internal'),false);
 }finally{global.fetch=prior;}
});
