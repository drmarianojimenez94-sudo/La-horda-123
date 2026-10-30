import sys,unittest
sys.path.insert(0,"crypto-agent")
from strategy_safety_v7 import prefix_invariance,risk_report,choose_with_validation
from strategy_tournament_v7 import signals

class SafetyTests(unittest.TestCase):
 def test_reject_unprofitable(self):
  r=risk_report({"trades":20,"return_pct":-1,"max_drawdown_pct":2})
  self.assertFalse(r["eligible"])
 def test_reject_insufficient_trades(self):
  self.assertFalse(risk_report({"trades":1,"return_pct":5,"max_drawdown_pct":1})["eligible"])
 def test_prefix_causality(self):
  bars=[{"open":100+i*.01,"high":101+i*.01,"low":99+i*.01,
         "close":100+i*.01,"volume":1000} for i in range(260)]
  self.assertTrue(prefix_invariance(signals,bars,[120,160,200])["passed"])
 def test_cash_when_no_validated_candidate(self):
  self.assertIsNone(choose_with_validation({"ranking":[{"strategy":"cash",
   "validation_mean_return_pct":0}],"per_asset":{}})["candidate"])

if __name__=="__main__":unittest.main()
