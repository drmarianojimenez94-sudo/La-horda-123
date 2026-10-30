import sys,unittest
sys.path.insert(0,"crypto-agent")
from training_memory_v5 import make_record

class MemoryTests(unittest.TestCase):
 def test_immutable_record_fields(self):
  report={"folds":[{"return_pct":-1.5}],"no_live_orders":True}
  record=make_record(report,"12345","abc","simulation",365)
  self.assertEqual(record["run_id"],"12345")
  self.assertEqual(record["history_days"],365)
  self.assertEqual(record["report"],report)
  self.assertEqual(len(record["report_sha256"]),64)
 def test_reject_invalid_run_id(self):
  with self.assertRaises(ValueError):make_record({},"abc","abc","simulation",365)

if __name__=="__main__":unittest.main()
