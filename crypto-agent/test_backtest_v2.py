import importlib.util
import unittest
from datetime import datetime,timedelta,timezone
spec=importlib.util.spec_from_file_location("bt","crypto-agent/backtest_v2.py")
bt=importlib.util.module_from_spec(spec);spec.loader.exec_module(bt)

class TestBacktestV2(unittest.TestCase):
 def test_no_future_data_in_signal(self):
  bars=[dict(open=100+i*.01,high=101+i*.01,low=99+i*.01,close=100+i*.01,volume=1000) for i in range(220)]
  a=bt.signal(bars,bt.PARAMETERS[0])
  bars2=bars+[dict(open=1,high=10000,low=1,close=10000,volume=1000)]
  self.assertEqual(a,bt.signal(bars2[:-1],bt.PARAMETERS[0]))
 def test_flat_market_no_trades(self):
  start=datetime(2026,1,1,tzinfo=timezone.utc)
  data={"BTCUSDT":{(start+timedelta(hours=i)).isoformat():dict(open=100.,high=100.,low=100.,close=100.,volume=1000.) for i in range(600)}}
  times=list(data["BTCUSDT"])
  result=bt.simulate(data,bt.PARAMETERS[0],times[200],times[-1])
  self.assertEqual(result["trades"],0)
  self.assertEqual(result["final"],200.)
 def test_no_leverage(self):
  self.assertLessEqual(bt.ROUND_TRIP,0.01)
if __name__=="__main__":unittest.main()
