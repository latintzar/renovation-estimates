from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
origin=os.environ.get('NATIVE_TEST_ORIGIN','http://127.0.0.1:4190');base=origin+os.environ.get('NATIVE_TEST_BASE_PATH','/apps/estimates');checks={}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 for width,height in [(1600,1000),(390,844)]:
  c=b.new_context(viewport={'width':width,'height':height},reduced_motion='reduce');page=c.new_page();foreign=[];errors=[]
  c.route('**/*',lambda route:route.continue_() if route.request.url.startswith((origin,'data:','blob:')) else(foreign.append(route.request.url.split('/')[2]),route.abort())[-1]);page.on('pageerror',lambda e:errors.append(str(e)))
  r=page.goto(base+os.environ.get('NATIVE_TEST_ENTRY',''),wait_until='networkidle');page.locator('a[href$="/listing/101"]').wait_for();checks[f'root_native_feed_{width}']=r.status==200 and page.url==base+'/listings'
  page.locator('a[href$="/listing/101"]').click();page.get_by_text('La vivienda conserva acabados antiguos y una distribución aprovechable. Este caso usa medidas y observaciones de ejemplo.',exact=True).wait_for();checks[f'native_report_{width}']=True
  page.get_by_role('button',name='Presupuesto desglosado',exact=True).click();page.get_by_role('heading',name='Presupuesto desglosado',exact=True).wait_for();checks[f'detailed_budget_{width}']=page.get_by_text('Precios y medidas ficticios de ejemplo',exact=False).count()>0
  if width==1600 and os.environ.get('NATIVE_TEST_SCREENSHOT'):page.screenshot(path=os.environ['NATIVE_TEST_SCREENSHOT'],full_page=True)
  checks[f'budget_record_metadata_{width}']=page.get_by_text('74 m² construidos',exact=True).count()>0 and page.get_by_text('Gràcia · vivienda de ejemplo',exact=True).count()>0 and page.get_by_text('Por asignar',exact=True).count()>0
  checks[f'budget_overflow_{width}']=not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
  page.emulate_media(media='print');checks[f'print_has_quantity_and_total_{width}']=page.get_by_text('SYNTH-FLOOR',exact=False).count()>0 and page.get_by_text('P.E.M.',exact=False).count()>0;page.emulate_media(media='screen')
  page.get_by_role('button',name='Close report',exact=True).click()
  checks[f'close_budget_{width}']=page.get_by_role('button',name='Presupuesto desglosado',exact=True).is_visible()
  checks[f'provider_post_denied_{width}']=c.request.post(base+'/api/listings/101/run-pipeline',data={}).status==503
  checks[f'unknown_provider_get_denied_{width}']=c.request.get(base+'/api/admin/runs').status==503
  checks[f'cached_detailed_rows_{width}']=len(c.request.get(base+'/api/renovation/101/v048/packages').json()['packages'][0]['line_items'])==24
  checks[f'no_external_or_script_error_{width}']=not foreign and not errors
  c.close()
 b.close()
Path(os.environ.get('NATIVE_TEST_RESULT','/tmp/estimate-native-interaction-proof.json')).write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2));assert all(checks.values())
