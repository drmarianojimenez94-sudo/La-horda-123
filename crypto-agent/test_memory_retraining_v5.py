import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,"crypto-agent")
from learner_v4 import FEATURES,fit
from memory_reuse_v5 import previous_weights
from meta_v5 import train

class MemoryRetrainingTests(unittest.TestCase):
 def test_warm_start_requires_old_completed_fold(self):
  with tempfile.TemporaryDirectory() as directory:
   report={"folds":[{"cal_end":"2026-01-01","model_snapshots":{
       "trend":{"weights":[.1]*len(FEATURES)}}}]}
   digest=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":")).encode()).hexdigest()
   Path(directory,"1.json").write_text(json.dumps({"report":report,"report_sha256":digest,"run_id":"1"}))
   self.assertEqual(previous_weights("2026-02-01",directory)["trend"]["source_run"],"1")
   self.assertEqual(previous_weights("2025-12-01",directory),{})
 def test_corrupt_memory_ignored(self):
  with tempfile.TemporaryDirectory() as directory:
   Path(directory,"1.json").write_text(json.dumps({"report":{"folds":[]},"report_sha256":"bad"}))
   self.assertEqual(previous_weights("2026-02-01",directory),{})
 def test_warm_start_weights_are_used(self):
  samples=[{"strategy":"trend","regime":"bull","pnl":1} for _ in range(40)]
  weights=[.1]*len(FEATURES)
  model=fit(samples,epochs=0,initial_weights=weights)
  self.assertEqual(model,tuple(weights))
 def test_missing_specialists_still_fail_closed(self):
  models,counts=train([],"01","02","03")
  self.assertEqual(models,{})
  self.assertEqual(counts["calibration_positive"],0)

if __name__=="__main__":unittest.main()
