import sys,unittest
sys.path.insert(0,"crypto-agent")
from preflight_v5 import preflight
from labels_v5 import label_opportunities
from specialists_v5 import specialists

class FastV5Tests(unittest.TestCase):
 def test_short_history_fails_fast(self):
  self.assertEqual(preflight({"BTCUSDT":{}})["reason"],"insufficient_history")
 def test_feature_window_is_sufficient(self):
  bars=[{"open":100.,"high":101.,"low":99.,"close":100.,"volume":20000.,
         "quote_volume":2000000.} for _ in range(121)]
  self.assertEqual(specialists(bars),[])
 def test_no_future_label_in_short_series(self):
  self.assertEqual(label_opportunities({"BTCUSDT":{}},step=12),[])

if __name__=="__main__":unittest.main()
