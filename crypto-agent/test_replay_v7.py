import sys,unittest
sys.path.insert(0,"crypto-agent")
from replay_v7 import replay
from synthetic_quotes_v7 import generate

class ReplayTests(unittest.TestCase):
 def test_offline_replay_has_no_live_orders(self):
  report=replay(generate(1000),horizon_ms=5000)
  self.assertTrue(report["no_real_orders"])
  self.assertGreaterEqual(report["final_equity"],0)
  self.assertEqual(sum(report["sample_counts"].values())>0,True)
 def test_too_short_fails(self):
  with self.assertRaises(ValueError):replay(generate(50))
 def test_deterministic(self):
  a=replay(generate(600),horizon_ms=5000)
  b=replay(generate(600),horizon_ms=5000)
  self.assertEqual(a["return_pct"],b["return_pct"])

if __name__=="__main__":unittest.main()
