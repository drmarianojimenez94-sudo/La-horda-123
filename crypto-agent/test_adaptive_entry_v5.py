import sys,unittest
sys.path.insert(0,"crypto-agent")
from meta_v5 import train,select
from backtest_v5 import run

class AdaptiveEntryTests(unittest.TestCase):
 def test_threshold_derived_without_test_labels(self):
  rows=[]
  for i in range(100):
   row={"signal_time":f"{i:04d}","label_end":f"{i+1:04d}",
        "strategy":"trend","regime":"bull","score":.1,
        "net_return":.01 if i%3 else -.01,"pnl":.01 if i%3 else -.01,
        "label":int(i%3!=0)}
   rows.append(row)
  _,a=train(rows,"0050","0080","0101")
  changed=[dict(r,label=1-r["label"],net_return=-r["net_return"],pnl=-r["pnl"]) if r["signal_time"]>="0080" else r for r in rows]
  _,b=train(changed,"0050","0080","0101")
  self.assertEqual(a["selected_threshold"],b["selected_threshold"])
  self.assertGreater(a["selected_threshold"],0)
 def test_untrained_signals_still_rejected(self):
  self.assertEqual(select([{"symbol":"BTCUSDT","strategy":"trend"}],{},threshold=.0001),[])

if __name__=="__main__":unittest.main()
