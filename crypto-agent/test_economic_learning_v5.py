import sys,unittest
sys.path.insert(0,"crypto-agent")
from learner_v4 import vector,FEATURES
from labels_v5 import label_opportunities
from meta_v5 import select
from diagnostics_v5 import diagnose

class EconomicLearningTests(unittest.TestCase):
 def test_feature_alignment(self):
  sample={"strategy":"trend","regime":"bull","momentum_1h":.01,"relative_volume":2}
  self.assertEqual(len(vector(sample)),len(FEATURES))
 def test_threshold_exactly_ten_percent_lower(self):
  self.assertEqual(select.__defaults__[-1],.0018)
  self.assertEqual(diagnose.__defaults__[-1],.0018)
 def test_net_label_uses_future_open_and_costs(self):
  data={}
  for i in range(160):
   t=f"{i:04d}"
   price=100+i*.1
   data[t]={"timestamp":t,"open":price,"high":price+1,"low":price-1,
            "close":price,"volume":20000,"quote_volume":2000000}
  rows=label_opportunities({"BTCUSDT":data},step=1,horizon=3)
  for row in rows:
   self.assertLess(row["signal_time"],row["entry_time"])
   self.assertLess(row["entry_time"],row["label_end"])
   self.assertEqual(row["label_policy"],"next_open_to_post_horizon_open_net_of_costs")

if __name__=="__main__":unittest.main()
