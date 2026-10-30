import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v9_diagnostics import classify_regime, walk_forward_regimes, trade_attribution, causal_prior_weights, regime_validation

class V9DiagnosticsTest(unittest.TestCase):
    def test_no_future_leak(self):
        bars=[{"close":100+i*.1} for i in range(300)]
        original=classify_regime(bars,288)
        bars[288]["close"]=999999
        self.assertEqual(original,classify_regime(bars,288))
    def test_folds_disjoint(self):
        bars=[{"close":100} for _ in range(900)]
        folds=walk_forward_regimes(bars,288,900)
        self.assertTrue(all(a["end"]==b["start"] for a,b in zip(folds,folds[1:])))
    def test_cost_reconciliation(self):
        journal=[{"kind":"buy","symbol":"BTC","qty":1,"price":100,"fee":.1},
                 {"kind":"sell","symbol":"BTC","qty":1,"price":102,"fee":.102,"reason":"target"}]
        r=trade_attribution(journal,200)
        self.assertAlmostEqual(r["net_pnl"],1.798)
        self.assertAlmostEqual(r["net_return_pct"],.899)
    def test_memory_cutoff(self):
        runs=[{"trained_until_ms":100,"ranked":[{"id":"a","validation_mean_pct":2}]},
              {"trained_until_ms":200,"ranked":[{"id":"a","validation_mean_pct":99}]}]
        self.assertEqual(causal_prior_weights(runs,200)["a"],2)
    def test_regime_rejects_loss(self):
        result=regime_validation([{"regime":"bull","trades":30,"net_return_pct":1},
                                  {"regime":"bear","trades":30,"net_return_pct":-1}])
        self.assertFalse(result["approved"])

if __name__=="__main__":unittest.main()
