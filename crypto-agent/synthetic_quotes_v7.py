"""Deterministic synthetic quote stream for engine smoke tests only.
NOT historical market data; returns must never be presented as strategy evidence.
"""
import argparse,json,math
from pathlib import Path

def generate(n=2400):
    rows=[]
    for i in range(n):
        mid=100+1.5*math.sin(i/30)+.003*i
        rows.append({"timestamp_ms":1000000+i*1000,"symbol":"BTCUSDT",
                     "bid":round(mid-.025,6),"ask":round(mid+.025,6),
                     "bid_qty":10+(i%7),"ask_qty":8+(i%9)})
    return rows

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    a=p.parse_args();Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    with open(a.output,"w") as f:
        for row in generate():f.write(json.dumps(row)+"\n")
