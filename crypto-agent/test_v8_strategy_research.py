import sys,unittest
sys.path.insert(0,"crypto-agent")
from v8_strategy_research import universe,signal,simulate,evaluate
class V8ResearchTests(unittest.TestCase):
 def bars(self,n=1100):
  return {f"{i:05d}":{"open":100+i*.01,"high":100.2+i*.01,
          "low":99.8+i*.01,"close":100+i*.01,"volume":1000+i%9}
          for i in range(n)}
 def test_fifty_unique_candidates(self):
  u=universe()
  self.assertEqual(len(u),50)
  self.assertEqual(len({x["id"] for x in u}),50)
  self.assertEqual(len({x["family"] for x in u}),5)
 def test_no_future_dependency(self):
  b=list(self.bars().values())
  for c in universe():
   self.assertEqual(signal(b[:500],499,c),signal(b,499,c))
 def test_validation_only_and_no_forced_winner(self):
  r=evaluate({"BTCUSDT":self.bars()})
  self.assertEqual(r["candidates"],50)
  self.assertEqual(r["tested"],50)
  self.assertTrue(r["selection_policy"].startswith("validation_only"))
  self.assertFalse(r["real_orders"])
 def test_fees_and_trades(self):
  b=list(self.bars().values())
  r=simulate(b,universe()[0],700,900)
  self.assertGreaterEqual(r["fees"],0)
  self.assertGreaterEqual(r["trades"],0)
if __name__=="__main__":unittest.main()
