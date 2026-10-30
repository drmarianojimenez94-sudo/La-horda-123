import sys,unittest
sys.path.insert(0,"crypto-agent")
from diagnostics_v5 import diagnose,calibration_diagnostics

class DiagnosticsTests(unittest.TestCase):
 def test_missing_model_explained(self):
  rows=[{"symbol":"BTCUSDT","strategy":"trend"}]
  self.assertEqual(diagnose(rows,{})[0]["reason"],"specialist_unavailable")
 def test_no_calibration_samples(self):
  self.assertEqual(calibration_diagnostics([],{})["trend"]["status"],"no_samples")
 def test_no_threshold_bypass(self):
  rows=[{"symbol":"BTCUSDT","strategy":"trend","score":0}]
  self.assertEqual(diagnose(rows,{})[0]["reason"],"specialist_unavailable")

if __name__=="__main__":unittest.main()
