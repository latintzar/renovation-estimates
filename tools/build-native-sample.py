#!/usr/bin/env python3
"""Build cached native report contracts with original BOQ math and authored inputs."""
from pathlib import Path
import argparse,asyncio,importlib.util,json,tempfile,sqlite3,hashlib
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('first_estimate',ROOT/'tools/first-estimate.py');first=importlib.util.module_from_spec(spec);spec.loader.exec_module(first)
ROOMS=[('living','Salón',24,20),('kitchen','Cocina',12,14),('bathroom','Baño',6,10),('entry','Entrada',8,12)]
RATES=[('floor','SYNTH-FLOOR','Suelo cerámico · precio de ejemplo','m2',32,.5,'flooring','area_floor_m2'),('paint','SYNTH-PAINT','Preparación y pintura · precio de ejemplo','m2',11,.15,'painting','area_wall_m2'),('skirt','SYNTH-SKIRT','Rodapié · precio de ejemplo','ml',8,.1,'flooring','perimetro_room_ml'),('light','SYNTH-LIGHT','Punto de luz · precio de ejemplo','ud',65,1,'electrical','cantidad_lights_ud'),('socket','SYNTH-SOCKET','Toma eléctrica · precio de ejemplo','ud',45,.7,'electrical','cantidad_sockets_ud'),('door','SYNTH-DOOR','Ajuste de carpintería · precio de ejemplo','ud',140,1.5,'carpentry','cantidad_doors_ud')]

def build():
 with tempfile.TemporaryDirectory(prefix='estimate-native-cache-') as name,first.network_fence() as attempts:
  directory=Path(name);assembler,formula,catalogue,lookup_module,source=first.original_modules();catalogue.validate_catalog()
  prices=directory/'prices.sqlite'
  with sqlite3.connect(prices) as con:
   con.execute('create table price_book(id text primary key,price real,unit text,short_desc text,full_desc text,desc_100 text)')
   con.executemany('insert into price_book values(?,?,?,?,?,?)',[(code,price,unit,desc,desc,desc) for _,code,desc,unit,price,_,_,_ in RATES])
  lookup=lookup_module.BCCAPriceLookup(prices);reports=[]
  for ix,title in enumerate(['Piso para reformar en Gràcia','Apartamento con luz en Sant Antoni','Vivienda con terraza en Sants']):
   listing_id=101+ix;matches=[];plans=[];signals={};factor=1+ix*.12
   for room_id,room_name,area,perimeter in ROOMS:
    signals[room_id]={k:{'value':v} for k,v in {'area_floor_m2':round(area*factor,2),'area_wall_m2':round(perimeter*2.6*factor,2),'perimetro_room_ml':round(perimeter*factor,2),'cantidad_lights_ud':2,'cantidad_sockets_ud':4,'cantidad_doors_ud':1}.items()}
    for key,code,desc,unit,price,hours,system,signal in RATES:
     item=lookup.get_price(code);wid=room_id+'-'+key
     matches.append({'work_item_id':wid,'room_id':room_id,'bcca_code':item.code,'bcca_desc_100':item.short_desc,'unit':item.unit,'unit_price':item.price,'labor_hours_per_unit':hours})
     plans.append({'work_item_id':wid,'formula_ast':{'op':'SIGNAL','signal_id':signal}})
   plan={'plans':plans};assembler._plans_validate_or_raise(plan=plan,bcca_matches_by_item={m['work_item_id']:m for m in matches});sink=first.LocalBoqSink(directory/('boq-'+str(listing_id)+'.sqlite'))
   saved=asyncio.run(assembler.assemble_v4_boq(listing_id=listing_id,strategy_name='market_standard',dimension='surface_finishes',bcca_matches=matches,quant_plan=plan,signals_by_room=signals,db=sink,listing_sqm=74+ix*8,match_mode='authored-synthetic-price-book'))
   rows=sink.rows();assert saved==24
   for row in rows:
    wid=row['provenance']['work_item_id'];key=wid.split('-')[-1];rate=next(r for r in RATES if r[0]==key);row.update(item_id=wid,room_id=row['room_name'],room_name=next(r[1] for r in ROOMS if r[0]==row['room_name']),system=rate[6],price_basis='Precios y medidas ficticios de ejemplo')
   pem=round(sum(x['line_total'] for x in rows),2);total=round(pem*1.19*1.10,2);hours=round(sum(x.get('labor_hours',0) for x in rows),2)
   gallery=['/images/landing/no-es-magia/before.webp']+['/images/landing/rooms/'+x[0]+'.webp' for x in ROOMS]
   listing={'id':listing_id,'source_url':'','source_domain':'example.invalid','title':title,'description':'Vivienda ficticia para explorar el informe completo. Fotografías generadas y recuperadas del proyecto original; medidas, precios y comparables de ejemplo.','price_eur':195000+ix*24000,'bedrooms':2+ix%2,'bathrooms':1,'sqm':74+ix*8,'m2_built':74+ix*8,'m2_useful':65+ix*7,'listing_type':'sale','price_period':'total','address':['Gràcia · vivienda de ejemplo','Sant Antoni · vivienda de ejemplo','Sants · vivienda de ejemplo'][ix],'city':'Barcelona','neighborhood':['Gràcia','Sant Antoni','Sants'][ix],'country':'Spain','condition':'renovate','property_subtype':'flat','has_elevator':True,'has_balcony':True,'has_terrace':ix==2,'photos':gallery,'image_urls':gallery,'pipeline_status':'complete','created_at':'2026-10-28T09:00:00Z','updated_at':'2026-10-28T09:00:00Z'}
   comps=[]
   for j,role in enumerate(['below','reference','above']):
    price=round((listing['price_eur']+total)*(1+(j-1)*.08));comps.append({'id':listing_id*10+j,'casafari_property_id':None,'sale_price':price,'price_per_sqm':round(price/listing['sqm']),'total_area':listing['sqm']+j*2,'bedrooms':listing['bedrooms'],'bathrooms':1,'condition':'good','distance_km':.3+j*.2,'address':'Comparable ficticio '+str(j+1)+' · '+listing['neighborhood'],'property_url':'','photo_urls':['/images/landing/no-es-magia/after-fair_market.webp'],'comp_role':role,'coordinates':None,'source':'authored-synthetic-comparable'})
   summary={'concept':{'intro_before':'La vivienda conserva acabados antiguos y una distribución aprovechable. Este caso usa medidas y observaciones de ejemplo.','intro_after':'La propuesta renueva suelos, pintura, puntos eléctricos y carpintería por estancia.','design_style':'Reforma por estancias','key_upgrades':['Suelos continuos','Pintura y acabados','Puntos eléctricos'],'value_story':'Cada partida conserva su medida, fórmula y precio de ejemplo.'},'property_summary':{'address':listing['address'],'total_cost':total,'total_weeks':4},'rooms':[{'room_id':rid,'room_name':rn,'estimated_m2':round(a*factor,2),'tagline':'Acabados y electricidad','key_changes':['Suelo cerámico y rodapié','Pintura de paredes','Puntos de luz y tomas'],'cost':round(sum(x['line_total'] for x in rows if x['room_id']==rid),2),'weeks':'1–2','packages':[]} for rid,rn,a,per in ROOMS],'timeline':{'total_weeks':4,'summary':'Plan de ejemplo de cuatro semanas, organizado por estancias y oficios.'}}
   pkg={'package_type':'market_standard','strategy_name':'market_standard','total_cost':total,'renovation_cost':total,'grand_total_with_iva':total,'line_items_count':len(rows),'line_items':rows,'duration_weeks':4,'total_labor_hours':hours,'eli5_summary':summary,'dimension_totals':{'surface_finishes':pem},'room_images':[{'room_id':'living','room_name':'Salón','before_image':gallery[0],'after_image':'/images/landing/no-es-magia/after-fair_market.webp','key_changes':['Suelos y pintura','Iluminación y carpintería'],'is_hero':True}],'before_image':gallery[0],'after_image':'/images/landing/no-es-magia/after-fair_market.webp','comparables':comps,'reference_sold_price':comps[1]['sale_price'],'reference_comparable_id':comps[1]['id'],'price_basis':'Precios y medidas ficticios de ejemplo','confidence_score':None,'sanity_check_passed':True,'risk_flags':[]}
   reports.append({'listing':listing,'package':pkg,'comparables':comps,'calculation':{'saved_rows':saved,'pem_subtotal':pem,'total_with_source_report_overheads_and_tax':total,'labor_hours':hours,'measurements':signals}})
  assert not attempts
 return {'fixture':'authored-native-workspace-v1','original_commit':first.UPSTREAM_COMMIT,'calculation_source':source,'calculation':'Original _plans_validate_or_raise, assemble_v4_boq, quantity_formula_v4, measurement_catalog_v4 and BCCAPriceLookup. Authored measured signals and synthetic SQLite price book; no model planning or market data.','provider_model_calls':0,'network_attempts':0,'reports':reports}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'frontend/src/fixtures/native-workspace.json');args=parser.parse_args();data=build();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n');print(json.dumps({'reports':len(data['reports']),'rows':sum(len(x['package']['line_items']) for x in data['reports']),'network_attempts':0,'provider_model_calls':0}))
