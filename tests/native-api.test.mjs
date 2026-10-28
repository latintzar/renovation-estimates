import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {nativeSampleResponse} from '../frontend/src/lib/sample/response.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('../frontend/src/fixtures/native-workspace.json',import.meta.url)));
const get=(path,method='GET',search=new URLSearchParams())=>nativeSampleResponse(fixture,path,method,search,'/apps/estimates');
test('native catalogue and report contract share all cached property rows',()=>{
 const rows=get('/api/listings').body.data;assert.equal(rows.length,3);
 for(const row of rows){assert.ok(row.photos.every(p=>p.startsWith('/apps/estimates/images/')));const report=get('/api/renovation/'+row.id+'/v048/packages').body;assert.equal(report.packages.length,1);assert.equal(report.packages[0].line_items.length,24);assert.ok(report.packages[0].eli5_summary.rooms.length>=4);assert.equal(get('/api/listings/'+row.id+'/comparables').body.comparables.length,3);}
});
test('cached prices reproduce exact original BOQ totals, with authored provenance',()=>{
 assert.equal(fixture.provider_model_calls,0);assert.equal(fixture.network_attempts,0);
 for(const row of fixture.reports){const items=row.package.line_items;assert.equal(row.calculation.saved_rows,24);for(const item of items){assert.equal(item.line_total,item.quantity*item.unit_price);assert.ok(item.bcca_code.startsWith('SYNTH-'));assert.equal(item.provenance.pipeline,'v4');}assert.equal(Math.round(items.reduce((sum,item)=>sum+item.line_total,0)*100),Math.round(row.calculation.pem_subtotal*100));}
});
test('read-only sample rejects writes, arbitrary provider paths and missing records',()=>{
 for(const method of ['POST','PUT','DELETE','PATCH'])assert.equal(get('/api/listings/101',method).status,503);
 for(const path of ['/api/listings/101/run-pipeline','/api/scrape','/api/admin/runs','/api/listings/example.id/analysis','/api/listings/101/../../secret'])assert.equal(get(path).status,503);
 assert.equal(get('/api/listings/999').status,404);
 assert.equal(get('/api/listings', 'GET',new URLSearchParams('limit=1&offset=1')).body.data[0].id,102);
});
