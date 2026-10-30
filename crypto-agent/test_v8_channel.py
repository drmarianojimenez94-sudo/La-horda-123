import sys,unittest
sys.path.insert(0,"crypto-agent")
from v8_channel_signals import updated_stop
from v8_shared_portfolio import SharedPortfolio

class ChannelTests(unittest.TestCase):
 def test_stop_never_moves_down(self):
  self.assertEqual(updated_stop(100,101,2),100)
 def test_shared_cash(self):
  p=SharedPortfolio()
  self.assertTrue(p.buy("BTCUSDT",100,{"BTCUSDT":100,"ETHUSDT":100}))
  self.assertTrue(p.buy("ETHUSDT",100,{"BTCUSDT":100,"ETHUSDT":100}))
  self.assertLess(p.cash,200)
 def test_round_trip_cost(self):
  p=SharedPortfolio()
  p.buy("BTCUSDT",100,{"BTCUSDT":100})
  p.sell("BTCUSDT",100)
  self.assertLess(p.cash,200)
if __name__=="__main__":unittest.main()
