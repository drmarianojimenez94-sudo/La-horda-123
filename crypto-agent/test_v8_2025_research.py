import csv,sys,tempfile,unittest,datetime as dt
from pathlib import Path
sys.path.insert(0,"crypto-agent")
from download_year_v8 import parse_timestamp
from v8_2025_research import hourly_from_5m

class Historical2025Tests(unittest.TestCase):
 def test_millisecond_and_microsecond_exchange_timestamps(self):
  self.assertEqual(parse_timestamp("1735689600000").year,2025)
  self.assertEqual(parse_timestamp("1735689600000000").year,2025)
 def test_partial_year_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/"BTCUSDT.csv"
   with path.open("w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["timestamp","open","high","low","close","volume","quote_volume"])
    w.writerow(["2025-01-01T00:00:00+00:00",100,101,99,100,1,100])
   with self.assertRaises(ValueError):hourly_from_5m(folder)
if __name__=="__main__":unittest.main()
