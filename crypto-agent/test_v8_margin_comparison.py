import sys,unittest
sys.path.insert(0,"crypto-agent")
from v8_margin_comparison import margin_simulate,compare_selected
from v8_strategy_research import universe

class MarginComparisonTests(unittest.TestCase):
 def test_margin_scenarios(self):
  bars=[{"open":100+i*.01,"high":100.1+i*.01,"low":99.9+i*.01,
         "close":100+i*.01,"volume":1000} for i in range(350)]
  result=margin_simulate(bars,universe()[0],220,340,leverage=1.5)
  self.assertTrue(result["paper_only"])
  self.assertGreaterEqual(result["liquidations"],0)
 def test_cash_fallback(self):
  self.assertEqual(compare_selected({},None)["status"],"cash_selected")
if __name__=="__main__":unittest.main()
