import sys,unittest
sys.path.insert(0,"crypto-agent")
from meta_v5 import train,select
from walkforward_v5 import validate

class V5MetaTests(unittest.TestCase):
 def test_empty_model_does_not_trade(self):
  self.assertEqual(select([{"symbol":"BTC","strategy":"trend"}],{}),[])
 def test_purged_training(self):
  rows=[{"signal_time":"01","label_end":"02","strategy":"trend","net_return":.01,"label":1},
        {"signal_time":"03","label_end":"04","strategy":"trend","net_return":-.01,"label":0},
        {"signal_time":"05","label_end":"06","strategy":"trend","net_return":.02,"label":1}]
  models,counts=train(rows,"03","05","07")
  self.assertEqual({k:counts[k] for k in ("train","calibration","test")},
                   {"train":1,"calibration":1,"test":1})
  self.assertGreater(counts["selected_threshold"],0)
  self.assertEqual(models,{})
 def test_short_history_rejected(self):
  with self.assertRaises(ValueError):validate({"BTC":{"a":{"close":100}}})

if __name__=="__main__":unittest.main()
