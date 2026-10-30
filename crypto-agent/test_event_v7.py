import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,"crypto-agent")
from event_engine_v7 import EventPaperAgent,BookEvent,features
from event_memory_v7 import EventMemory

class V7Tests(unittest.TestCase):
 def book(self,t=1000):
  return BookEvent(t,"BTCUSDT",100.,100.05,10.,10.)
 def test_fee_spread_gate(self):
  a=EventPaperAgent()
  self.assertIsNone(a.on_book(self.book(),.001))
  self.assertEqual(a.snapshot()["fills"],0)
 def test_positive_edge_paper_only(self):
  a=EventPaperAgent()
  self.assertIsNotNone(a.on_book(self.book(),.01))
  self.assertEqual(a.snapshot()["fills"],1)
  self.assertLess(a.portfolio.cash,200)
 def test_stale_and_out_of_order(self):
  a=EventPaperAgent()
  self.assertIsNone(a.on_book(self.book(),.01,now_ms=8000))
  self.assertIsNotNone(a.on_book(self.book(),.01))
  self.assertIsNone(a.on_book(self.book(),.01))
  self.assertEqual(a.rejections["out_of_order"],1)
 def test_memory_survives_restart(self):
  with tempfile.TemporaryDirectory() as folder:
   path=str(Path(folder)/"memory.db")
   m=EventMemory(path);m.record("book_ticker","BTC",{"bid":100},1000)
   m.save_model("v7-1",1000,{"weights":[1,2]},{"brier":.2});m.close()
   m=EventMemory(path)
   self.assertEqual(m.recent()[0]["payload"]["bid"],100)
   self.assertEqual(m.models()[0]["parameters"]["weights"],[1,2])
   m.close()

if __name__=="__main__":unittest.main()
