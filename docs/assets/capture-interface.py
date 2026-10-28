#!/usr/bin/env python3
"""Capture the actual Estimate listing shell and importer; empty local API fixture."""
from pathlib import Path
import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=Path(__file__).resolve().parent


def main():
    with socket.socket() as owned:
        owned.bind(('127.0.0.1',0));port=owned.getsockname()[1]
    origin='http://127.0.0.1:'+str(port)
    env={name:value for name,value in os.environ.items() if name in ('PATH','HOME','LANG','LC_ALL')}
    env.update({'NEXT_TELEMETRY_DISABLED':'1','NODE_ENV':'production','BACKEND_URL':'http://127.0.0.1:9'})
    log=Path(tempfile.mkdtemp(prefix='estimate-interface-server-'))/'server.log'
    with log.open('w') as stream:
        server=subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port',str(port)],cwd=ROOT/'frontend',env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+30
            while True:
                try:
                    with urllib.request.urlopen(origin+'/listings',timeout=1) as response:
                        if response.status==200:break
                except Exception:
                    if time.monotonic()>deadline or server.poll() is not None:raise RuntimeError('Owned preview server did not become ready.')
                    time.sleep(.1)
            foreign=[];api=[];errors=[];shots=[]
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                for label,width,height in [('desktop',1600,1000),('phone',390,844)]:
                    context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,locale='en-US',reduced_motion='reduce')
                    def route(request_route):
                        url=urllib.parse.urlparse(request_route.request.url)
                        if url.scheme=='http' and url.netloc=='127.0.0.1:'+str(port):
                            if url.path.startswith('/api/'):
                                api.append({'method':request_route.request.method,'path':url.path})
                                if request_route.request.method!='GET':raise RuntimeError('Capture must not submit an import.')
                                request_route.fulfill(status=200,content_type='application/json',body=json.dumps({'success':True,'data':[],'total':0}))
                            else:request_route.continue_()
                        else:
                            foreign.append({'host':url.hostname,'path':url.path});request_route.abort()
                    context.route('**/*',route)
                    page=context.new_page();page.on('pageerror',lambda error:errors.append(type(error).__name__))
                    page.goto(origin+'/',wait_until='networkidle')
                    if not page.url.endswith('/listings'):raise RuntimeError('App entry redirect failed.')
                    page.evaluate('document.fonts.ready')
                    buttons=page.get_by_role('button')
                    buttons.first.wait_for(state='visible')
                    listing=OUTPUT/('listings-'+label+'.png');page.screenshot(path=listing,animations='disabled')
                    candidate=page.get_by_role('button',name=re.compile('paste|add|pegar|añadir|propiedad|anuncio',re.I))
                    if candidate.count()==0:raise RuntimeError('Original import control was not found.')
                    candidate.first.click()
                    field=page.locator('input').first;field.wait_for(state='visible')
                    field.fill('https://example.invalid/home')
                    page.wait_for_function("""() => { const button=document.querySelector('button[type=submit]'); return button && getComputedStyle(button).opacity==='1'; }""")
                    importer=OUTPUT/('import-'+label+'.png');page.screenshot(path=importer,animations='disabled')
                    page.goto(origin+'/first-estimate',wait_until='networkidle')
                    page.get_by_role('button',name='View report',exact=True).click()
                    page.get_by_role('cell',name='Synthetic example · authored demonstration rates',exact=True).wait_for()
                    report_text=page.locator('body').inner_text()
                    if 'BCCA Andalucía 2024' in report_text or 'Peón ordinario' in report_text or 'Formato Orden' in report_text:raise RuntimeError('Unowned reference pricing or certification copy reached the fixture.')
                    if 'Synthetic floor finish' not in report_text or 'Synthetic skirting' not in report_text:raise RuntimeError('Actual calculated fixture rows are absent.')
                    report=OUTPUT/('estimate-report-'+label+'.png')
                    page.screenshot(path=report,animations='disabled')
                    shots.append({'path':report.name,'sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'width':width,'height':height})
                    bounds=page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                    if bounds['scroll']>bounds['width']+1:raise RuntimeError('Interface overflows the viewport.')
                    for shot in (listing,importer):shots.append({'path':shot.name,'sha256':hashlib.sha256(shot.read_bytes()).hexdigest(),'width':width,'height':height})
                    context.close()
                browser.close()
            if foreign or errors:raise RuntimeError('Unexpected foreign request or browser exception.')
            files={}
            for parent in ('frontend/src','frontend/public/fonts'):
                for file in sorted((ROOT/parent).rglob('*')):
                    if file.is_file():files[file.relative_to(ROOT).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
            proof={'upstream_commit':'4dca5f9bd94a3ee4759dff949f3d185acd095022','surface':'Original Estimate components in the reviewed portable source derivative','state':'Empty listing API fixture and original paste modal; synthetic example.invalid URL; import unsubmitted','api_fixture_requests':api,'foreign_requests':foreign,'browser_exceptions':errors,'provider_model_calls':0,'device_scale_factor':1,'screenshots':shots,'source_hashes':files}
            (OUTPUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
            print(json.dumps({'screenshots':len(shots),'foreign_requests':len(foreign),'browser_exceptions':len(errors),'provider_model_calls':0}))
        finally:
            server.terminate();server.wait(timeout=10)


if __name__=='__main__':main()
