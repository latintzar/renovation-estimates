#!/usr/bin/env python3
"""Connect a real synthetic costing receipt to the original report interface."""
from pathlib import Path
import argparse
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('first_estimate',ROOT/'tools/first-estimate.py')
calculation=importlib.util.module_from_spec(spec);spec.loader.exec_module(calculation)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    _,receipt=calculation.run_proof()
    fixture={'fixture':'authored-synthetic-v1','calculation_source':receipt['source'],
             'line_items':[dict(row, system='flooring') for row in receipt['rows']],'pem_subtotal':receipt['totals']['amount_eur'],
             'labor_hours':receipt['totals']['labor_hours']}
    destination=ROOT/'frontend/src/fixtures/first-estimate.json'
    text=json.dumps(fixture,indent=2,sort_keys=True,allow_nan=False)+'\n'
    if args.check:
        if not destination.exists() or destination.read_text()!=text:raise SystemExit('First-result fixture needs regeneration.')
    else:
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(text)
    print(json.dumps({'fixture':fixture['fixture'],'rows':len(fixture['line_items']),'synthetic_subtotal_eur':fixture['pem_subtotal'],'checked':args.check}))


if __name__=='__main__':main()
