import unittest
from futures_research import eligible, simulate_isolated_long

class FuturesResearchTests(unittest.TestCase):
 def test_gate_rejects_weak_evidence(self):
  self.assertFalse(eligible(.7,20,3.5,.02,True,True))
  self.assertFalse(eligible(.6,200,3.5,.02,True,True))
  self.assertFalse(eligible(.7,200,2.,.02,True,True))
  self.assertTrue(eligible(.7,200,3.5,.02,True,True))
 def test_funding_and_fees_reduce_profit(self):
  result=simulate_isolated_long(100,101,100,2,9)
  self.assertFalse(result['liquidated'])
  self.assertLess(result['pnl'],2)
  self.assertGreater(result['funding'],0)
 def test_liquidation_and_input_validation(self):
  self.assertTrue(simulate_isolated_long(100,90,100,2,8,lowest_price=40)['liquidated'])
  with self.assertRaises(ValueError):
   simulate_isolated_long(100,101,100,5,8)

if __name__=='__main__':unittest.main()
