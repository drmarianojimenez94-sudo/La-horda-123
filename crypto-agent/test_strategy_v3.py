import sys,unittest
sys.path.insert(0,"crypto-agent")
from strategy_v3 import aggregate,classify,allocate,Config,decision
class V3Tests(unittest.TestCase):
 def test_completed_aggregation(self):
  bars=[dict(timestamp=str(i),open=1.,high=2.,low=.5,close=1.,volume=1.) for i in range(13)]
  self.assertEqual(len(aggregate(bars,12)),1)
  self.assertEqual(aggregate(bars,12)[0]["volume"],12)
 def test_risk_stop(self):
  self.assertEqual(allocate(200,200,0,.02,daily_loss=.03),0)
  self.assertEqual(allocate(200,200,0,.02,drawdown=.11),0)
 def test_no_signal_with_insufficient_history(self):
  self.assertIsNone(decision([],200,200))
  self.assertEqual(classify([]),"unknown")
if __name__=="__main__":unittest.main()
