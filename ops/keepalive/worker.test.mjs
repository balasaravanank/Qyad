import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('./worker.js',import.meta.url),'utf8');
const worker=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).default;
test('checks the exact health URL and validates ok',async()=>{
 const old=globalThis.fetch;let called=false;
 try {globalThis.fetch=async(url,opts)=>{called=true;assert.equal(url.href,'https://api.example.com/api/v1/health');assert.equal(opts.redirect,'error');return Response.json({ok:true});};await worker.scheduled({}, {HEALTH_URL:'https://api.example.com/api/v1/health'});assert.equal(called,true);} finally {globalThis.fetch=old;}
});
test('rejects insecure, credentialed or wrong endpoints',async()=>{
 for(const url of ['http://api.example.com/api/v1/health','https://api.example.com/private','https://a:b@api.example.com/api/v1/health','https://api.example.com/api/v1/health?token=x']) await assert.rejects(worker.scheduled({}, {HEALTH_URL:url}));
});
test('fails on unhealthy status or body',async()=>{
 const old=globalThis.fetch;
 try{for(const response of [new Response('',{status:503}),Response.json({ok:false})]){globalThis.fetch=async()=>response;await assert.rejects(worker.scheduled({}, {HEALTH_URL:'https://api.example.com/api/v1/health'}));}}finally{globalThis.fetch=old;}
});
