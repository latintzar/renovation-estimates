/** Fail closed except for one verified, dev-only advisory false positive. */
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

const advisory='https://github.com/advisories/GHSA-g3hv-75wg-m249';
export function evaluateAudit(report,lock) {
  if(report.error || !report.vulnerabilities || !lock.packages)throw new Error('Complete npm audit and lock data are required.');
  const entries=report.vulnerabilities;
  const devOnly=entry=>Array.isArray(entry.nodes)&&entry.nodes.length>0&&entry.nodes.every(node=>lock.packages[node]?.dev===true);
  function accepted(name) {
    const seen=new Set(), reviewedLeaves=new Set();
    function visit(current) {
      if(seen.has(current))return true; // npm reports peer-dependency cycles.
      const entry=entries[current];
      if(!entry||!Array.isArray(entry.via)||!entry.via.length||!devOnly(entry))return false;
      seen.add(current);
      return entry.via.every(via=> {
        if(typeof via==='string')return visit(via);
        const exact=current==='minimatch'&&entry.nodes.every(node=>lock.packages[node]?.version==='3.1.5')&&via&&via.name==='minimatch'&&via.url===advisory;
        if(exact)reviewedLeaves.add(current);
        return exact;
      });
    }
    return visit(name)&&reviewedLeaves.size>0;
  }
  return {blocked:Object.keys(entries).filter(name=>!accepted(name)),reviewed:Object.keys(entries).filter(name=>accepted(name))};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const processResult=spawnSync('npm',['audit','--json'],{encoding:'utf8',maxBuffer:10*1024*1024});
    if(processResult.error||![0,1].includes(processResult.status))throw new Error('npm audit did not complete.');
    const report=JSON.parse(processResult.stdout),lock=JSON.parse(readFileSync('package-lock.json','utf8'));
    const result=evaluateAudit(report,lock);
    if(result.reviewed.length)console.log('Reviewed dev-only minimatch3.1.5 graph: '+advisory+' describes optimizationLevel>=2 preprocessing absent from this legacy API.');
    if(result.blocked.length) {
      console.error('Unreviewed dependency advisories: '+result.blocked.join(', '));
      process.exitCode=1;
    }else console.log('Dependency audit passed; every remaining advisory is the exact reviewed dev-only exception.');
  }catch(error){console.error(error.message);process.exitCode=1;}
}
