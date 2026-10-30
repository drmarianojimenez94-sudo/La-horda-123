import sys,unittest
sys.path.insert(0,"crypto-agent")
from champion_v5 import evaluate,metrics,fingerprint

def report(returns,drawdowns=None):
 return {"data_fingerprint":"frozen-dataset-1",
         "folds":[{"cal_end":str(i),"test_end":str(i+1),"return_pct":r,"fills":2,"fees":.1}
                  for i,r in enumerate(returns)]}

class ChampionTests(unittest.TestCase):
 def test_no_unverified_promotion(self):
  self.assertFalse(evaluate(report([1,1]))["promote"])
 def test_worse_rejected(self):
  self.assertFalse(evaluate(report([1,1]),report([2,2]))["promote"])
 def test_better_comparable_accepted(self):
  self.assertTrue(evaluate(report([3,3]),report([1,1]))["promote"])
 def test_noncomparable_rejected(self):
  other=report([1,1]);other["folds"][0]["test_end"]="different"
  self.assertEqual(evaluate(report([3,3]),other)["reason"],"noncomparable_oos_windows")
 def test_missing_data_hash_rejected(self):
  a=report([3,3]);b=report([1,1]);a.pop("data_fingerprint")
  self.assertFalse(evaluate(a,b)["promote"])
 def test_no_trades_rejected(self):
  a=report([2,2])
  for f in a["folds"]:f["fills"]=0
  self.assertFalse(evaluate(a,report([1,1]))["promote"])

if __name__=="__main__":unittest.main()
