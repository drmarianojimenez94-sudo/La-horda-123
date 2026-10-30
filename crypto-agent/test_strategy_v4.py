import sys
import unittest
sys.path.insert(0,"crypto-agent")
from backtest_v4 import calibrate, benchmark
from strategy_v3 import Config, candidates
from learner_v4 import fit,predict,vector
from v4_extension import SCENARIOS,simulate_partial_fill,fit_platt,calibrated_probability
from dataclasses import replace
from backtest_v3 import run

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

    def test_learner_requires_history(self):
        self.assertIsNone(fit([{"strategy":"trend","regime":"bull","pnl":1}]))

    def test_learner_uses_only_training_rows(self):
        rows=[{"strategy":"trend","regime":"bull","pnl":1.0,"stop_distance":.02,"reward_risk":2.4} for _ in range(45)]
        model=fit(rows)
        self.assertIsNotNone(model)
        p=predict(model,rows[0])
        self.assertGreater(p,.5)
        self.assertEqual(len(vector(rows[0])),len(model))

    def test_calibration_changes_live_probability(self):
        model=fit_platt([.2]*20+[.8]*20,[0]*20+[1]*20)
        self.assertIsNotNone(model)
        self.assertGreater(calibrated_probability(.8,model),calibrated_probability(.2,model))

    def test_partial_fill_and_stress(self):
        bar={"open":100.,"high":102.,"low":98.,"close":100.,"volume":.1,"quote_volume":10.}
        normal=simulate_partial_fill(100.,bar,SCENARIOS[0])
        adverse=simulate_partial_fill(100.,bar,SCENARIOS[1])
        self.assertLess(normal["filled_notional"],100.)
        self.assertLess(adverse["filled_notional"],normal["filled_notional"])
        self.assertGreater(adverse["price"],normal["price"])

    def test_empty_strategy_preserves_cash(self):
        bars={str(i).zfill(5):{"timestamp":str(i).zfill(5),"open":100.,"high":101.,"low":99.,"close":100.,"volume":100.} for i in range(20)}
        result=run({"BTCUSDT":bars},"00005","00019",replace(Config(),enabled_strategies=()))
        self.assertEqual(result["trades"],0)
        self.assertEqual(result["final"],200.)

    def test_benchmark(self):
        data={"BTCUSDT":{"a":{"open":100,"close":100},"b":{"open":100,"close":110}}}
        self.assertAlmostEqual(benchmark(data,"a","z")["BTCUSDT"],10)
        self.assertIsNone(benchmark(data,"a","z")["ETHUSDT"])

if __name__=="__main__":
    unittest.main()
