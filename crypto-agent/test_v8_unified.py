import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,"crypto-agent")
from v8_unified_ledger import UnifiedSpotLedger
from v8_run_memory import store_run,prior_candidates
from v8_strategy_research import universe,simulate

class UnifiedV8Tests(unittest.TestCase):
 def test_two_asset_shared_cash_and_reconciliation(self):
  p=UnifiedSpotLedger()
  prices={"BTC":100.,"ETH":100.}
  self.assertTrue(p.buy("BTC",100,prices))
  self.assertTrue(p.buy("ETH",100,prices))
  self.assertLessEqual(p.exposure(prices),60.)
  p.sell("BTC",100);p.sell("ETH",100)
  self.assertTrue(p.reconcile({})["reconciled"])
  self.assertLess(p.cash,200)
 def test_single_engine_tournament(self):
  bars=[{"open":100+i*.01,"high":100.1+i*.01,"low":99.9+i*.01,
         "close":100+i*.01,"volume":1000} for i in range(400)]
  self.assertTrue(simulate(bars,universe()[0],200,350)["reconciled"])
 def test_memory_immutable_and_causal(self):
  with tempfile.TemporaryDirectory() as d:
   db=str(Path(d)/"v8.db")
   r={"selected":"channel","ranked":[]}
   store_run(r,db,"r1",1000)
   self.assertEqual(prior_candidates(db,999),[])
   self.assertEqual(len(prior_candidates(db,1001)),1)
   store_run(r,db,"r1",1000)
   with self.assertRaises(ValueError):store_run({"selected":"other"},db,"r1",1000)
if __name__=="__main__":unittest.main()
