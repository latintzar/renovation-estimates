import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateAudit} from './check-npm-audit.mjs';
const known={name:'minimatch',url:'https://github.com/advisories/GHSA-g3hv-75wg-m249'};
function fixture({version='3.1.5',dev=true,via=known}={}) {
 return {report:{vulnerabilities:{minimatch:{nodes:['node_modules/minimatch'],via:[via]},eslint:{nodes:['node_modules/eslint'],via:['minimatch']}}},lock:{packages:{'node_modules/minimatch':{version,dev},'node_modules/eslint':{version:'9.39.4',dev:true}}}};
}
test('only the reviewed legacy dev graph passes',()=>{const {report,lock}=fixture();assert.deepEqual(evaluateAudit(report,lock).blocked,[]);});
for(const [name,options] of [['modern affected version',{version:'9.0.9'}],['runtime dependency',{dev:false}],['new advisory',{via:{name:'minimatch',url:'https://github.com/advisories/GHSA-new-advisory'}}]])test(name+' remains blocking',()=>{const {report,lock}=fixture(options);assert.deepEqual(evaluateAudit(report,lock).blocked,['minimatch','eslint']);});
test('missing lock provenance fails closed',()=>{const {report,lock}=fixture();delete lock.packages['node_modules/minimatch'];assert.deepEqual(evaluateAudit(report,lock).blocked,['minimatch','eslint']);});
test('incomplete registry result fails closed',()=>assert.throws(()=>evaluateAudit({error:{code:'EAUDIT'}},{packages:{}})));

test('peer cycles still trace exclusively to the exact reviewed advisory',()=>{const {report,lock}=fixture();report.vulnerabilities.minimatch.via.push('eslint');assert.deepEqual(evaluateAudit(report,lock).blocked,[]);});
test('a cycle without reviewed leaf evidence remains blocking',()=>{const {report,lock}=fixture();report.vulnerabilities.minimatch.via=['eslint'];assert.deepEqual(evaluateAudit(report,lock).blocked,['minimatch','eslint']);});
