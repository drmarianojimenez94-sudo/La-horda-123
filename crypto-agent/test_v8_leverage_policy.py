import sys,unittest
sys.path.insert(0,"crypto-agent")
from v8_leverage_policy import leverage_decision,leverage_scenarios

class LeverageTests(unittest.TestCase):
 def test_losses_never_qualify(self):
  self.assertFalse(leverage_decision({"trades":100,"return_pct":-1,"max_drawdown_pct":2})["approved"])
 def test_low_sample_rejected(self):
  self.assertEqual(leverage_decision({"trades":5,"return_pct":10,"max_drawdown_pct":1})["reason"],"insufficient_validation_trades")
 def test_stress_gate(self):
  good={"trades":100,"return_pct":4,"max_drawdown_pct":2}
  self.assertFalse(leverage_decision(good,requested=2,stress_move=.1)["approved"])
 def test_no_live_orders(self):
  good={"trades":100,"return_pct":4,"max_drawdown_pct":2}
  self.assertTrue(leverage_decision(good,requested=1.5)["paper_only"])
 def test_never_exceed_two(self):
  good={"trades":100,"return_pct":4,"max_drawdown_pct":2}
  self.assertFalse(leverage_decision(good,requested=3)["approved"])

if __name__=="__main__":unittest.main()
