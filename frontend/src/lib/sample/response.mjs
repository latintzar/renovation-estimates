/** Cached report API contract for the actual native review workspace. Read-only. */
export function nativeSampleResponse(fixture,path,method,search=new URLSearchParams(),base='') {
  const setup={status:503,body:{success:false,code:'RECIPIENT_SERVICE_REQUIRED',error:'Configura tus proveedores para esta acción.'}};
  if(method!=='GET'&&method!=='HEAD')return setup;
  const prefix=value=>Array.isArray(value)?value.map(prefix):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([k,v])=>[k,prefix(v)])):typeof value==='string'&&value.startsWith('/images/')?base+value:value;
  const ok=body=>({status:200,body:prefix(body)});
  if(path==='/api/health')return ok({status:'ok',mode:'cached-native-sample',providers_enabled:false});
  if(path==='/api/listings'){
    const bound=(n,fallback,max)=>Number.isFinite(Number(n))&&n!==null?Math.max(0,Math.min(max,Math.floor(Number(n)))):fallback;
    const offset=bound(search.get('offset'),0,fixture.reports.length),limit=bound(search.get('limit'),50,50);
    return ok({success:true,data:fixture.reports.slice(offset,offset+limit).map(report=>report.listing)});
  }
  const match=path.match(/^\/api\/(listings|renovation)\/(\d+)(.*)$/);
  if(!match)return setup;
  const report=fixture.reports.find(row=>String(row.listing.id)===match[2]);
  if(!report)return {status:404,body:{success:false,error:'Elige una vivienda del catálogo.'}};
  const [_,kind,id,tail]=match;
  if(kind==='listings') {
    if(!tail)return ok({success:true,data:report.listing});
    if(tail==='/photos')return ok({success:true,data:report.listing.photos});
    if(tail==='/comparables')return ok({success:true,hasCoordinates:false,target:{id:report.listing.id,title:report.listing.title,address:report.listing.address,lat:null,lng:null},comparables:report.comparables});
    if(tail==='/translations')return ok({success:true,translations:{},data:{}});
    if(tail==='/photo-clusters')return ok({success:true,data:[]});
    if(tail==='/room-analyses')return ok({success:true,data:report.calculation.measurements});
  }
  if(kind==='renovation'){
    if(tail==='/v048/packages')return ok({success:true,hasData:true,packages:[report.package],strategy_selection:{selected_strategy:'market_standard'},sample_basis:fixture.fixture});
    if(tail==='/v048/status')return ok({success:true,status:'complete',current_stage:'cached_report',completed_stages:0,total_stages:0,queued_jobs:0,in_progress_jobs:0,source:'authored-cached-report',providers_enabled:false});
    if(tail==='/comparables/brackets'){
      const comps=report.comparables,brackets={fast_sell:comps[0].sale_price,fair_market:comps[1].sale_price,premium:comps[2].sale_price,count:comps.length,comparables:comps};
      return ok({success:true,hasCoordinates:false,data:{asking_price:report.listing.price_eur,casafari:brackets,filtered:brackets,filter_tolerance:0}});
    }
  }
  return setup;
}
