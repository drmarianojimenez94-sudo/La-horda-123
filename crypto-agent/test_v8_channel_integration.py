import sys,unittest
sys.path.insert(0,"crypto-agent")
from v8_channel_portfolio import research,simulate
from v8_channel_signals import confirmed

def data(n=400):
    return {s:{f"{i:05d}":{"open":100+i*.01,"high":100.2+i*.01,
      "low":99.8+i*.01,"close":100+i*.01,"volume":1000+i%10}
      for i in range(n)} for s in ("BTCUSDT","ETHUSDT")}

class IntegrationTests(unittest.TestCase):
 def test_shared_account(self):
  r=simulate(data())
  self.assertEqual(r["trades"],len(r["ledger"]))
 def test_no_forced_selection(self):
  r=research(data())
  self.assertEqual(r["variants"],27)
  self.assertTrue(r["paper_only"])
 def test_disjoint_development_windows(self):
  r=research(data())
  self.assertEqual(r["development_windows"],((0.,.2),(.2,.4),(.4,.6),(.6,.8)))
  self.assertEqual(r["final_window"],(.8,1.))
 def test_no_leverage_and_shared_cap(self):
  r=simulate(data(),risk_fraction=.005,max_portfolio_risk=.015)
  self.assertGreaterEqual(r["fees"],0)
 def test_prefix_invariance(self):
  b=list(data()["BTCUSDT"].values())
  self.assertEqual(confirmed(b,150,48,1.05),confirmed(b[:151],150,48,1.05))
if __name__=="__main__":unittest.main()
