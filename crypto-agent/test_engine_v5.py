import sys,unittest
sys.path.insert(0,"crypto-agent")
from engine_v5 import Portfolio
from paper_v5 import paper_fill,MarketConditions

class V5EngineTests(unittest.TestCase):
 def test_partial_buy_sell_and_reconciliation(self):
  p=Portfolio(200)
  p.place("buy","BTC", "buy",2)
  candle={"open":50,"high":51,"low":49,"close":50,"volume":1,"quote_volume":50}
  fill=paper_fill(p,"buy",candle,MarketConditions(participation=.5,fee=.001,spread=0,slippage=0))
  self.assertAlmostEqual(fill.quantity,.5)
  self.assertAlmostEqual(p.positions["BTC"],.5)
  self.assertAlmostEqual(p.equity({"BTC":50}),200-fill.fee)
  p.cancel("buy")
  p.place("sell","BTC","sell",.5)
  paper_fill(p,"sell",candle,MarketConditions(participation=1,fee=.001,spread=0,slippage=0))
  self.assertAlmostEqual(p.positions["BTC"],0)
  self.assertAlmostEqual(p.realized_pnl,-.05)
  p.reconcile({"BTC":50})
 def test_no_oversell(self):
  p=Portfolio()
  with self.assertRaises(ValueError):p.place("sell","BTC","sell",1)
 def test_no_negative_cash(self):
  p=Portfolio(1)
  p.place("b","BTC","buy",10)
  paper_fill(p,"b",{"open":10,"high":10,"low":10,"close":10,"volume":100})
  self.assertGreaterEqual(p.cash,-1e-9)
 def test_duplicate_order(self):
  p=Portfolio()
  p.place("a","BTC","buy",1)
  with self.assertRaises(ValueError):p.place("a","BTC","buy",1)

if __name__=="__main__":unittest.main()
