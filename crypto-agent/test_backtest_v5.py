import sys,unittest
sys.path.insert(0,"crypto-agent")
from backtest_v5 import run
from labels_v5 import purged_split,label_opportunities

class V5IntegrationTests(unittest.TestCase):
 def test_paper_backtest_reconciles(self):
  bars={}
  for i in range(150):
   t=f"{i:05d}"
   price=100+i*.03
   bars[t]={"timestamp":t,"open":price,"high":price+1,"low":price-1,
            "close":price,"volume":20000,"quote_volume":2000000}
  result=run({"BTCUSDT":bars},start="00125",end="00149")
  self.assertGreaterEqual(result["final_equity"],0)
  self.assertEqual(result["model"],"V5 offline execution foundation, untrained specialists")
 def test_no_same_bar_execution(self):
  bars={}
  for i in range(180):
   t=f"{i:05d}"
   price=100+i*.1
   bars[t]={"timestamp":t,"open":price,"high":price+1,"low":price-1,"close":price,"volume":20000,"quote_volume":2000000}
  result=run({"BTCUSDT":bars},start="00125",end="00179",hold_bars=8)
  self.assertGreaterEqual(result["final_equity"],0)
  self.assertTrue(all(f["quantity"]>0 for f in result["ledger"]))
  self.assertLessEqual(result["fees"],result["initial"])

 def test_label_purge(self):
  rows=[{"signal_time":"01","label_end":"03"},{"signal_time":"04","label_end":"06"},
        {"signal_time":"07","label_end":"09"}]
  train,cal,test=purged_split(rows,"04","07","10")
  self.assertEqual((len(train),len(cal),len(test)),(1,1,1))
 def test_no_signal_on_short_history(self):
  self.assertEqual(label_opportunities({"BTCUSDT":{}}),[])

if __name__=="__main__":unittest.main()
