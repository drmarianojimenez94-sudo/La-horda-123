import sys,unittest
sys.path.insert(0,"crypto-agent")
from v8_margin_ledger import MarginLedger
from v8_price_behaviour import characterize

class MarginTests(unittest.TestCase):
 def test_profitable_margin_reconciles(self):
  l=MarginLedger()
  l.open(100,20,2)
  l.close(110)
  self.assertGreater(l.cash,200)
  self.assertEqual(l.liquidations,0)
 def test_adverse_candle_liquidates(self):
  l=MarginLedger()
  l.open(100,20,2)
  self.assertEqual(l.mark(101,45,90),"liquidation")
  self.assertEqual(l.liquidations,1)
  self.assertIsNone(l.position)
 def test_no_leverage_over_two(self):
  with self.assertRaises(ValueError):MarginLedger().open(100,20,3)
 def test_equity_after_open(self):
  l=MarginLedger();l.open(100,20,2)
  self.assertLess(l.equity(100),200)
 def test_behaviour_data_type(self):
  self.assertEqual(characterize({})["data_type"],"real_historical_5m_OHLCV")

if __name__=="__main__":unittest.main()
