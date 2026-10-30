"""Durable append-only event memory using SQLite.
Paper-only events; no credentials. Store decisions, observations and outcomes.
"""
import json,sqlite3,time
from pathlib import Path

class EventMemory:
    def __init__(self,path="crypto-agent/state/v7-memory.sqlite3"):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(self.path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          observed_ms INTEGER NOT NULL,
          kind TEXT NOT NULL,
          symbol TEXT NOT NULL,
          payload TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS models(
          version TEXT PRIMARY KEY, trained_until_ms INTEGER NOT NULL,
          payload TEXT NOT NULL, metrics TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0)""")
        self.db.commit()
    def record(self,kind,symbol,payload,observed_ms=None):
        ts=int(time.time()*1000) if observed_ms is None else int(observed_ms)
        with self.db:
            self.db.execute("INSERT INTO events(observed_ms,kind,symbol,payload) VALUES(?,?,?,?)",
                            (ts,kind,symbol,json.dumps(payload,sort_keys=True)))
    def recent(self,kind=None,limit=100):
        sql="SELECT observed_ms,kind,symbol,payload FROM events"
        args=[]
        if kind is not None:sql+=" WHERE kind=?";args.append(kind)
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        return [dict(timestamp_ms=t,kind=k,symbol=s,payload=json.loads(p))
                for t,k,s,p in self.db.execute(sql,args)]
    def save_model(self,version,trained_until_ms,parameters,metrics):
        with self.db:
            self.db.execute("INSERT INTO models(version,trained_until_ms,payload,metrics) VALUES(?,?,?,?)",
                            (version,int(trained_until_ms),json.dumps(parameters),json.dumps(metrics)))
    def models(self):
        return [dict(version=v,trained_until_ms=t,parameters=json.loads(p),metrics=json.loads(m),active=bool(a))
                for v,t,p,m,a in self.db.execute("SELECT version,trained_until_ms,payload,metrics,active FROM models ORDER BY trained_until_ms DESC")]
    def close(self):self.db.close()
