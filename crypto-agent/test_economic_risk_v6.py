import sys,unittest
sys.path.insert(0,"crypto-agent")
from meta_v5 import select
from diagnostics_v5 import diagnose
from backtest_v5 import run

class EconomicRiskV6Tests(unittest.TestCase):
 def test_uncertainty_buffer_rejects_marginal_edge(self):
  from unittest.mock import patch
  signal={"symbol":"BTCUSDT","strategy":"trend"}
  model={"model":(0,),"calibration":(1,0),"win":.01,"loss":.01,
         "calibration_error":0,"return_standard_error":.08}
  with patch("meta_v5.predict",return_value=.7),patch("meta_v5.calibrated_probability",return_value=.7):
   self.assertEqual(select([signal],{"trend":model},threshold=.0001),[])
  with patch("diagnostics_v5.predict",return_value=.7),patch("diagnostics_v5.calibrated_probability",return_value=.7):
   self.assertEqual(diagnose([signal],{"trend":model},threshold=.0001)[0]["reason"],"insufficient_expected_net")
 def test_expired_buy_does_not_lock_symbol(self):
  data={}
  for i in range(160):
   t=f"{i:05d}"
   price=100+i*.04
   data[t]={"timestamp":t,"open":price,"high":price+1,"low":price-1,
            "close":price,"volume":0.,"quote_volume":0.}
  result=run({"BTCUSDT":data},start="00125",end="00159",hold_bars=3)
  self.assertGreaterEqual(result["final_equity"],0)
  self.assertEqual(result["fills"],0)

if __name__=="__main__":unittest.main()
