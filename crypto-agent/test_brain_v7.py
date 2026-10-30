import sys,unittest
sys.path.insert(0,"crypto-agent")
from calibration_v7 import calibration_report,recalibrate_candidate
from benchmarks_v7 import compare

class BrainTests(unittest.TestCase):
 def test_drift(self):
  rows=[{"imbalance":0,"spread":.001,"label":0,"net_return":-.01} for _ in range(40)]
  self.assertTrue(calibration_report({"weights":[5,0,0]},rows)["drift"])
 def test_no_automatic_promotion(self):
  rows=[{"imbalance":0,"spread":.001,"label":0,"net_return":-.01} for _ in range(80)]
  self.assertFalse(recalibrate_candidate(rows[:40],rows[40:])["promote"])
 def test_cash_reference(self):
  self.assertEqual(compare([])["cash_return"],0)

if __name__=="__main__":unittest.main()
