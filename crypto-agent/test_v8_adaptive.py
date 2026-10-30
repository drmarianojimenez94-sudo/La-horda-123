import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, "crypto-agent")
from v8_adaptive_selector import classify, select
from v8_adaptive_memory import record_outcome, historical_scores

class AdaptiveV8Tests(unittest.TestCase):
    def test_prefix_invariance(self):
        bars = [{"close":100+i*.1} for i in range(100)]
        self.assertEqual(classify(bars,80),classify(bars[:80],80))
    def test_no_forced_selection(self):
        self.assertIsNone(select("BTCUSDT","range",[{"id":"candidate"}],{}))
    def test_per_symbol_regime_selection(self):
        candidates=[{"id":"a"},{"id":"b"}]
        scores={("BTCUSDT","uptrend","a"):{"trades":25,"net_return_pct":2,"max_drawdown_pct":2},
                ("ETHUSDT","range","b"):{"trades":25,"net_return_pct":3,"max_drawdown_pct":2}}
        self.assertEqual(select("BTCUSDT","uptrend",candidates,scores)["id"],"a")
        self.assertEqual(select("ETHUSDT","range",candidates,scores)["id"],"b")
    def test_memory_cutoff(self):
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/"events.sqlite3")
            record_outcome(path,"BTCUSDT","uptrend","a",2.,100)
            record_outcome(path,"BTCUSDT","uptrend","a",-4.,200)
            self.assertEqual(historical_scores(path,150)[("BTCUSDT","uptrend","a")]["trades"],1)
            self.assertEqual(historical_scores(path,250)[("BTCUSDT","uptrend","a")]["trades"],2)

if __name__=="__main__":
    unittest.main()
