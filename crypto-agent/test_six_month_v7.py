import sys,unittest
sys.path.insert(0,"crypto-agent")
from benchmark_180d import report

class SixMonthTests(unittest.TestCase):
 def test_cash_and_buy_hold_baseline(self):
  data={"BTCUSDT":{"1":{"open":100,"close":100},"2":{"open":101,"close":110}}}
  r=report(data)
  self.assertEqual(r["cash_return_pct"],0)
  self.assertAlmostEqual(r["assets"]["BTCUSDT"]["buy_hold_return_pct"],10,places=8)
  self.assertIn("not_order_book",r["data_type"])

if __name__=="__main__":unittest.main()
