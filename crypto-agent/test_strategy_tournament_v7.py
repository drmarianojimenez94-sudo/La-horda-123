import sys,unittest
sys.path.insert(0,"crypto-agent")
from strategy_tournament_v7 import PARAMS,signals,simulate,tournament

def candles(n=360):
 out={}
 for i in range(n):
  p=100+i*.03
  out[f"{i:05d}"]={"open":p,"high":p+.1,"low":p-.1,"close":p,
                    "volume":1000+i%7}
 return out

class TournamentTests(unittest.TestCase):
 def test_strategies_have_distinct_rules(self):
  self.assertEqual(set(PARAMS),{"cash","trend_pullback","breakout_retest",
                                "volatility_breakout","mean_reversion"})
 def test_cash_reference(self):
  r=tournament({"BTCUSDT":candles()})
  self.assertEqual(r["per_asset"]["BTCUSDT"]["cash"]["test"]["return_pct"],0)
 def test_no_same_bar_signal(self):
  bars=list(candles().values())
  self.assertEqual(signals(bars,119),[])
 def test_fee_and_execution_nonnegative(self):
  bars=list(candles().values())
  r=simulate(bars,"trend_pullback",150,300)
  self.assertGreaterEqual(r["fees"],0)
  self.assertGreaterEqual(r["trades"],0)
 def test_no_forced_winner(self):
  r=tournament({"BTCUSDT":candles()})
  self.assertIn(r["selected_candidate"],list(PARAMS)+[None])

if __name__=="__main__":unittest.main()
