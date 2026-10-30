import sys,unittest
sys.path.insert(0,"crypto-agent")
from event_learning_v7 import build_shadow_labels,purged_time_split,drift_summary

def quote(t,bid,ask):
 return {"kind":"book_ticker","symbol":"BTCUSDT","timestamp_ms":t,
         "payload":{"bid":bid,"ask":ask,"bid_qty":10,"ask_qty":10}}

class EventLearningTests(unittest.TestCase):
 def test_future_bid_and_two_sided_cost(self):
  rows=[quote(1000,100,100.1),quote(2000,100.4,100.5),quote(3000,100.8,100.9)]
  samples=build_shadow_labels(rows,horizon_ms=1000,min_gap_ms=1000)
  self.assertEqual(len(samples),2)
  self.assertAlmostEqual(samples[0]["net_return"],100.4*.999/(100.1*1.001)-1)
  self.assertLess(samples[0]["signal_time_ms"],samples[0]["label_end_ms"])
 def test_no_future_no_label(self):
  self.assertEqual(build_shadow_labels([quote(1000,100,100.1)],1000),[])
 def test_purge_overlapping_labels(self):
  samples=build_shadow_labels([quote(t,100,100.1) for t in range(1000,8000,1000)],1000)
  train,cal,test=purged_time_split(samples,3000,5000,7000)
  self.assertTrue(all(s["label_end_ms"]<3000 for s in train))
  self.assertTrue(all(s["signal_time_ms"]>=3000 and s["label_end_ms"]<5000 for s in cal))
  self.assertTrue(all(s["signal_time_ms"]>=5000 and s["label_end_ms"]<7000 for s in test))
 def test_not_claiming_trained_model(self):
  self.assertFalse(drift_summary([])["ready"])

if __name__=="__main__":unittest.main()
