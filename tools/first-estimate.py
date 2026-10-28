#!/usr/bin/env python3
"""Run the original deterministic BOQ assembly with authored synthetic inputs.

Uses the real formula evaluator, measurement catalogue and SQLite price lookup.
Only the remote BOQ persistence sink is replaced with an owned local SQLite sink.
No photographs, model, scraping service or original price-book data are used.
"""
from __future__ import annotations
import argparse,asyncio,contextlib,hashlib,importlib,json,os,socket,sqlite3,sys,tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT='4dca5f9bd94a3ee4759dff949f3d185acd095022'
SOURCE_BLOBS={
 'pricing/v4_quantification_pipeline.py':'6c0306069a8d14a2f0b6d7d32830202a83998b94',
 'pricing/quantity_formula_v4.py':'27a2e1a4eb293635398849bbf1179fa75d516549',
 'pricing/measurement_catalog_v4.py':'452791bc955bbe6f6eb683dfd200ee633b9a4d51',
 'pricing/bcca_price_lookup.py':'240f9fe56b2f3eb26baa428ece761754e86e5d00',
}

@contextlib.contextmanager
def network_fence():
    """Fail on Python socket traffic during this deterministic proof, including DNS."""
    attempts=[];originals={}
    def denied(*args,**kwargs):
        attempts.append('blocked socket operation');raise RuntimeError('Synthetic estimate permits local files only.')
    for name in ('connect','connect_ex','sendto','sendmsg'):
        if hasattr(socket.socket,name):originals[(socket.socket,name)]=getattr(socket.socket,name);setattr(socket.socket,name,denied)
    originals[(socket,'getaddrinfo')]=socket.getaddrinfo;socket.getaddrinfo=denied
    try:yield attempts
    finally:
        for (owner,name),value in originals.items():setattr(owner,name,value)


def original_modules():
    source=ROOT/'backend';hashes={}
    for name,expected in SOURCE_BLOBS.items():
        raw=(source/name).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob!=expected:raise RuntimeError('Original calculation source differs from its reviewed pin: '+name)
        hashes[name]={'git_blob':blob,'sha256':hashlib.sha256(raw).hexdigest()}
    sys.dont_write_bytecode=True
    if str(source) not in sys.path:sys.path.insert(0,str(source))
    # Reviewed package imports: pricing.__init__ -> stdlib-only v2_scheduler.
    # V4 imports NumPy via its matcher; this proof never instantiates the matcher.
    assembler=importlib.import_module('pricing.v4_quantification_pipeline')
    formula=importlib.import_module('pricing.quantity_formula_v4')
    catalogue=importlib.import_module('pricing.measurement_catalog_v4')
    lookup=importlib.import_module('pricing.bcca_price_lookup')
    return assembler,formula,catalogue,lookup,hashes


def create_synthetic_prices(path:Path):
    with sqlite3.connect(path) as con:
        con.execute('create table price_book(id text primary key,price real,unit text,short_desc text,full_desc text,desc_100 text)')
        con.executemany('insert into price_book values(?,?,?,?,?,?)',[
            ('SYNTH-FLOOR-M2',20.0,'m2','Synthetic floor finish','Authored demonstration floor finish','Synthetic floor finish'),
            ('SYNTH-SKIRT-ML',5.0,'ml','Synthetic skirting','Authored demonstration skirting','Synthetic skirting'),
        ])
    path.chmod(0o600)


class LocalBoqSink:
    """Implements only the exact persistence call made by original assemble_v4_boq."""
    def __init__(self,path:Path):
        self.path=path
        with sqlite3.connect(path) as con:con.execute('create table estimate_rows(listing_id integer,strategy text,dimension text,room text,item_json text)')
        path.chmod(0o600)
    async def save_boq_line_items_batch(self,*,listing_id,strategy_name,dimension,room_name,items):
        with sqlite3.connect(self.path) as con:
            con.executemany('insert into estimate_rows values(?,?,?,?,?)',[(listing_id,strategy_name,dimension,room_name,json.dumps(item,sort_keys=True,allow_nan=False)) for item in items])
        return len(items)
    def rows(self):
        with sqlite3.connect(self.path) as con:return [json.loads(r[0]) for r in con.execute('select item_json from estimate_rows order by rowid')]


def synthetic_inputs(lookup):
    definitions=[('floor','SYNTH-FLOOR-M2','area_synthetic_floor_m2',0.5),('skirting','SYNTH-SKIRT-ML','perimetro_synthetic_room_ml',0.1)]
    matches=[];plans=[]
    for item_id,code,signal,hours in definitions:
        item=lookup.get_price(code)
        if item is None:raise RuntimeError('Synthetic price row is missing.')
        matches.append({'work_item_id':item_id,'room_id':'synthetic-room','bcca_code':item.code,'bcca_desc_100':item.short_desc,'unit':item.unit,'unit_price':item.price,'labor_hours_per_unit':hours})
        plans.append({'work_item_id':item_id,'formula_ast':{'op':'SIGNAL','signal_id':signal}})
    return matches,{'plans':plans},{'synthetic-room':{'area_synthetic_floor_m2':{'value':12.0},'perimetro_synthetic_room_ml':{'value':14.0}}}


async def assemble(assembler,sink,matches,plan,signals):
    return await assembler.assemble_v4_boq(listing_id=1,strategy_name='synthetic-first-result',dimension='surface_finishes',bcca_matches=matches,quant_plan=plan,signals_by_room=signals,db=sink,listing_sqm=60.0,match_mode='authored-synthetic-price-book')


def run_proof(output:Path|None=None):
    directory=Path(tempfile.mkdtemp(prefix='renovation-estimate-'));directory.chmod(0o700)
    with network_fence() as attempts:
        assembler,formula,catalogue,lookup_module,hashes=original_modules();catalogue.validate_catalog()
        create_synthetic_prices(directory/'synthetic-prices.sqlite3');lookup=lookup_module.BCCAPriceLookup(directory/'synthetic-prices.sqlite3')
        matches,plan,signals=synthetic_inputs(lookup);assembler._plans_validate_or_raise(plan=plan,bcca_matches_by_item={m['work_item_id']:m for m in matches});sink=LocalBoqSink(directory/'synthetic-estimate.sqlite3')
        saved=asyncio.run(assemble(assembler,sink,matches,plan,signals));rows=sink.rows()
        if saved!=2 or len(rows)!=2 or sum(r['line_total'] for r in rows)!=310.0:raise RuntimeError('Synthetic estimate differs from its exact expected result.')
        if attempts:raise RuntimeError('Unexpected network attempt occurred in the synthetic proof.')
    loaded={}
    for module in tuple(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file and Path(file).resolve().is_relative_to((ROOT/'backend').resolve()):
            source=Path(file).resolve();loaded[str(source.relative_to(ROOT/'backend'))]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt={'runtime':{'python':sys.version.split()[0],'numpy':getattr(sys.modules.get('numpy'),'__version__',None)},'loaded_original_modules':loaded,'fixture':'authored-synthetic-v1','upstream_commit':UPSTREAM_COMMIT,'source':hashes,'measurement_basis':{'area_synthetic_floor_m2':{'catalogue_signal':'room_floor_area_m2','unit':catalogue.get_measurement_signal_spec('room_floor_area_m2').unit_family},'perimetro_synthetic_room_ml':{'catalogue_signal':'room_perimeter_ml','unit':catalogue.get_measurement_signal_spec('room_perimeter_ml').unit_family}},'calculation':'Original _plans_validate_or_raise, assemble_v4_boq, quantity_formula_v4 and measurement_catalog_v4; original BCCAPriceLookup over synthetic SQLite','persistence':'owned local SQLite sink implements save_boq_line_items_batch only','rows':rows,'totals':{'quantity_floor_m2':12.0,'quantity_skirting_ml':14.0,'amount_eur':310.0,'labor_hours':7.4},'coverage':{'input_work_items':len(matches),'planned_work_items':len(plan['plans']),'saved_rows':saved,'all_fixture_work_items_saved':{r['provenance']['work_item_id'] for r in rows}=={m['work_item_id'] for m in matches}},'network_attempts':0,'provider_model_calls':0,'reference_data':'Synthetic rates/measurements only; construction/BCCA/reference data excluded.','state_directory':str(directory),'scope':'Deterministic pricing tail only; full listing/photo/model/queue/browser pipeline remains separate.'}
    target=output.expanduser().absolute() if output else directory/'first-estimate.json'
    if target.is_symlink() or target.resolve().is_relative_to(ROOT):raise RuntimeError('Choose a receipt path outside the source checkout.')
    if output and target.exists():raise RuntimeError('Choose a new receipt path.')
    target.parent.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'w') as stream:json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')
    return target,receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    path,receipt=run_proof(args.output)
    print(json.dumps({'receipt':str(path),'fixture':receipt['fixture'],'rows':len(receipt['rows']),'synthetic_amount_eur':receipt['totals']['amount_eur'],'network_attempts':0,'provider_model_calls':0}))
if __name__=='__main__':main()
