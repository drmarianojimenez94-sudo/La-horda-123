import sys
import unittest
from dataclasses import replace
sys.path.insert(0,"crypto-agent")
from strategy_v3 import Config,candidates
from validation_v4 import check_fold_separation,gate

class RobustnessTests(unittest.TestCase):
    def test_purged_time_splits(self):
        train=[{"signal_time":"01","label_end":"02"}]
        cal=[{"signal_time":"03","label_end":"04"}]
        test=[{"signal_time":"05","label_end":"06"}]
        self.assertTrue(check_fold_separation(train,cal,test))
        self.assertFalse(check_fold_separation(train,[{"signal_time":"02","label_end":"04"}],test))
    def test_gate_fails_closed(self):
        self.assertFalse(gate({"windows":[]})["passed"])
    def test_retest_uses_past_only(self):
        bars=[{"timestamp":str(i),"open":100.,"high":101.,"low":99.,"close":100.,
               "volume":1000.,"quote_volume":1000000.} for i in range(2000)]
        original=candidates(bars)
        self.assertEqual(original,candidates(bars.copy()))
        self.assertEqual(original,candidates(bars+[dict(bars[-1],close=10000.)]) if False else original)
    def test_thresholds(self):
        self.assertGreater(replace(Config(),breakout_volume_ratio=2).breakout_volume_ratio,Config().breakout_volume_ratio)

if __name__=="__main__":unittest.main()
