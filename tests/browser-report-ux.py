"""Cached report UX regression; requires Playwright/Chromium and PyMuPDF.
Run the sample app and set ESTIMATES_BASE_URL; every external origin/write is blocked.
"""
import asyncio,json,pathlib,os,tempfile
from urllib.parse import urlsplit
import fitz
from playwright.async_api import async_playwright
OUT=pathlib.Path(os.environ.get('ESTIMATES_PROOF_DIR',tempfile.mkdtemp(prefix='estimate-report-ux-')));OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('ESTIMATES_BASE_URL','http://127.0.0.1:3002').rstrip('/')
async def main():
 async with async_playwright()as p:
  browser=await p.chromium.launch(headless=True,executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM'),args=['--no-sandbox']);rows=[]
  for w in [320,390,768,1600]:
   page=await browser.new_page(viewport={'width':w,'height':900 if w>=768 else 844},has_touch=w<768,is_mobile=w<768);errors=[];blocked=[];checks={};page.on('pageerror',lambda e:errors.append(str(e)))
   async def fence(route):
    if route.request.method not in ['GET','HEAD','OPTIONS']or (not route.request.url.startswith(('data:','blob:')) and urlsplit(route.request.url).netloc != urlsplit(BASE).netloc):blocked.append(route.request.url);await route.abort()
    else:await route.continue_()
   await page.route('**/*',fence)
   def check(n,v):checks[n]=bool(v);assert v,n
   try:
    await page.goto(BASE+'/listings',wait_until='domcontentloaded');await page.locator('a[href*="listing/"]').first.click();trigger=page.get_by_role('button',name='Presupuesto desglosado',exact=True);await trigger.scroll_into_view_if_needed();scroll=await page.locator('#atelier-native-app').evaluate('e=>e.scrollTop');check('underlying_workspace_scrolled',scroll>200);await trigger.click();report=page.get_by_role('dialog',name='Presupuesto desglosado',exact=True);await report.wait_for();box=await report.bounding_box();check('native_fullscreen_after_scroll',await report.evaluate('e=>{let r=e.getBoundingClientRect();return e.matches(":modal")&&r.x===0&&r.y===0&&r.width===innerWidth&&r.height===innerHeight}'));check('report_no_horizontal_overflow',await report.evaluate('e=>e.scrollWidth<=e.clientWidth'));close=report.get_by_role('button',name='Close report',exact=True);check('close_hit44',await close.evaluate('e=>{let r=e.getBoundingClientRect();return r.width>=44&&r.height>=44}'));check('focus_starts_in_report',await close.evaluate('e=>e===document.activeElement'));await page.screenshot(path=str(OUT/f'estimates-{w}-fixed-report.png'));await report.evaluate('e=>e.scrollTop=1000');check('scrolled_controls_do_not_overlap',await report.locator('.estimate-report-controls').evaluate('e=>{let [a,b]=e.children;return a.getBoundingClientRect().bottom<=b.getBoundingClientRect().top+.5}'));await report.evaluate('e=>e.scrollTop=0')
    await page.keyboard.press('Shift+Tab');check('focus_wraps_inside',await report.evaluate('e=>e.contains(document.activeElement)'));await page.keyboard.press('Escape');await report.wait_for(state='detached');check('escape_returns_to_budget',await trigger.evaluate('e=>e===document.activeElement'));check('scroll_position_preserved',await page.locator('#atelier-native-app').evaluate(f'e=>Math.abs(e.scrollTop-{scroll})<2'));await trigger.click();await report.wait_for();await page.evaluate('()=>{window.printCalls=0;window.print=()=>{window.printCalls++};}');await report.get_by_role('button',name='Imprimir / PDF',exact=True).click();check('print_action_works',await page.evaluate('printCalls===1'))
    await page.emulate_media(media='print');check('print_contains_budget', '6528,77' in (await report.inner_text()).replace('\u00a0',''));check('print_isolates_report',await page.locator('#atelier-native-app').evaluate('e=>getComputedStyle(e).display==="none"'));check('print_unclipped',await report.evaluate('e=>getComputedStyle(e).overflow==="visible"'));await page.pdf(path=str(OUT/f'estimates-{w}-budget.pdf'),format='A4',print_background=True);pdf=fitz.open(OUT/f'estimates-{w}-budget.pdf');text=''.join(p.get_text()for p in pdf);check('pdf_contains_full_budget',pdf.page_count>=2 and '6528,77' in text and 'EXCLUSIONES' in text and 'Precios y cantidades' in text);pdf.close();await page.emulate_media(media='screen');await close.click();await report.wait_for(state='detached');check('close_returns_to_budget',await trigger.evaluate('e=>e===document.activeElement'));check('scroll_lock_released',await page.locator('#atelier-native-app').evaluate('e=>e.style.overflow!=="hidden"'));check('no_page_errors',not errors);rows.append({'width':w,'checks':checks,'box':box,'underlying_scroll':scroll,'errors':errors,'blocked':blocked,'passed':True})
   except Exception as e:rows.append({'width':w,'checks':checks,'error':str(e),'errors':errors,'blocked':blocked});await page.screenshot(path=str(OUT/f'estimates-{w}-regression-error.png'))
   (OUT/'estimates-regression.json').write_text(json.dumps({'base':BASE,'cases':rows},indent=2));await page.close()
  await browser.close();print(json.dumps(rows,indent=2));assert all(r.get('passed')for r in rows)
asyncio.run(main())
