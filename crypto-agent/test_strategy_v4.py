import sys
import unittest
sys.path.insert(0,"crypto-agent")
from backtest_v4 import calibrate, benchmark
from strategy_v3 import Config, candidates

class V4Tests(unittest.TestCase):
    def test_no_evidence_means_no_trading(self):
        enabled, priors, stats=calibrate([])
        self.assertEqual(enabled,())
        self.assertEqual(priors,())
        self.assertEqual(stats["trend"]["trades"],0)

    def test_profitable_training_strategy_is_selected(self):
        trades=[{"strategy":"trend","pnl":1.0} for _ in range(10)]
        enabled,priors,_=calibrate(trades)
        self.assertEqual(enabled,("trend",))
        self.assertGreater(dict(priors)["trend"],0.35)

    def test_losing_training_strategy_is_rejected(self):
        trades=[{"strategy":"breakout","pnl":-1.0} for _ in range(12)]
        enabled,_,_=calibrate(trades)
        self.assertEqual(enabled,())

    def test_benchmark(self):
        data={"BTCUSDT":{"a":{"open":100,"close":100},"b":{"open":100,"close":110}}}
        self.assertAlmostEqual(benchmark(data,"a","z")["BTCUSDT"],10)
        self.assertIsNone(benchmark(data,"a","z")["ETHUSDT"])

if __name__=="__main__":
    unittest.main()
