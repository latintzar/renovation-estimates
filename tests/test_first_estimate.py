"""Offline tests of the exact original pricing tail with authored synthetic data."""
import asyncio,copy,importlib.util,json,math,os,socket,tempfile,unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('first_estimate',Path(__file__).resolve().parents[1]/'tools/first-estimate.py');proof=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(proof)

class FirstEstimateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with proof.network_fence() as attempts:cls.assembler,cls.formula,cls.catalogue,cls.lookup_module,cls.hashes=proof.original_modules()
  assert attempts==[]
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='estimate-unit-');self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name);proof.create_synthetic_prices(self.directory/'prices.sqlite3');self.lookup=self.lookup_module.BCCAPriceLookup(self.directory/'prices.sqlite3');self.matches,self.plan,self.signals=proof.synthetic_inputs(self.lookup);self.sink=proof.LocalBoqSink(self.directory/'boq.sqlite3')
 def assemble(self):
  with proof.network_fence() as attempts:count=asyncio.run(proof.assemble(self.assembler,self.sink,self.matches,self.plan,self.signals))
  self.assertEqual(attempts,[]);return count
 def test_real_price_lookup_and_exact_original_totals(self):
  self.assertEqual(self.lookup.get_price('SYNTH-FLOOR-M2').price,20.0);self.assertIsNone(self.lookup.get_price('SYNTH-ABSENT'));self.assertEqual(self.assemble(),2)
  rows=self.sink.rows();self.assertEqual([r['quantity'] for r in rows],[12.0,14.0]);self.assertEqual([r['line_total'] for r in rows],[240.0,70.0]);self.assertEqual(sum(r['line_total'] for r in rows),310.0);self.assertAlmostEqual(sum(r['labor_hours'] for r in rows),7.4)
 def test_every_fixture_item_and_signal_has_provenance(self):
  self.catalogue.validate_catalog();self.assemble();rows=self.sink.rows();self.assertEqual({r['provenance']['work_item_id'] for r in rows},{m['work_item_id'] for m in self.matches});self.assertEqual({s for r in rows for s in r['provenance']['signals_used']},{'area_synthetic_floor_m2','perimetro_synthetic_room_ml'});self.assertTrue(all(r['provenance']['formula_ast']['op']=='SIGNAL' for r in rows))
 def test_original_plan_validator_requires_full_coverage(self):
  self.assembler._plans_validate_or_raise(plan=self.plan,bcca_matches_by_item={m['work_item_id']:m for m in self.matches})
  self.plan['plans'].pop()
  with self.assertRaisesRegex(RuntimeError,'missing plans'):
   self.assembler._plans_validate_or_raise(plan=self.plan,bcca_matches_by_item={m['work_item_id']:m for m in self.matches})
  self.assertEqual(self.sink.rows(),[])
 def test_missing_signal_fails_before_persistence(self):
  del self.signals['synthetic-room']['area_synthetic_floor_m2']
  with self.assertRaises(self.formula.FormulaValidationError):self.assemble()
  self.assertEqual(self.sink.rows(),[])
 def test_mismatched_units_fail_before_persistence(self):
  self.matches[0]['unit']='ud'
  with self.assertRaises(self.formula.FormulaValidationError):self.assemble()
  self.assertEqual(self.sink.rows(),[])
 def test_plan_must_join_an_existing_work_item(self):
  self.plan['plans'][0]['work_item_id']='unmatched-plan'
  with self.assertRaises(RuntimeError):self.assemble()
  self.assertEqual(self.sink.rows(),[])
 def test_unsupported_formula_is_rejected(self):
  self.plan['plans'][0]['formula_ast']={'op':'EVAL','value':'synthetic-only'}
  with self.assertRaises(self.formula.FormulaValidationError):self.assemble()
  self.assertEqual(self.sink.rows(),[])
 def test_negative_and_nonfinite_quantities_fail(self):
  for value in (-12.0,float('nan'),float('inf')):
   with self.subTest(value=str(value)):
    self.signals['synthetic-room']['area_synthetic_floor_m2']['value']=value
    with self.assertRaises(self.formula.FormulaValidationError):self.assemble()
    self.assertEqual(self.sink.rows(),[])
 def test_original_area_cap_is_applied(self):
  self.signals['synthetic-room']['area_synthetic_floor_m2']['value']=100.0;self.assemble();row=self.sink.rows()[0];self.assertEqual(row['quantity'],60*.35);self.assertEqual(row['line_total'],420.0)
 def test_network_fence_blocks_before_transport(self):
  with proof.network_fence() as attempts:
   with self.assertRaises(RuntimeError):socket.getaddrinfo('synthetic.example.invalid',443)
  self.assertEqual(len(attempts),1)

if __name__=='__main__':unittest.main()
