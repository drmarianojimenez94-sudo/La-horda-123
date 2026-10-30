"""Research-only backtest v2: causal fills, regime filters, trade ledger and walk-forward validation."""
import csv, json, math, statistics
from collections import defaultdict
from pathlib import Path

INITIAL=200.0
FEE=0.001
HALF_SPREAD=0.0003
SLIPPAGE=0.0005
ROUND_TRIP=2*(FEE+HALF_SPREAD+SLIPPAGE)
BARS_PER_HOUR=12
PARAMETERS=[
 {"fast":144,"slow":864,"momentum":72,"threshold":0.002,"stop":2.0,"reward":2.0},
 {"fast":288,"slow":1440,"momentum":144,"threshold":0.004,"stop":2.5,"reward":2.5},
 {"fast":432,"slow":2016,"momentum":144,"threshold":0.006,"stop":3.0,"reward":2.0},
]
def load_data(folder="crypto-agent/data_5m"):
 out={}
 for path in Path(folder).glob("*.csv"):
  with path.open() as f:
   rows=[dict(timestamp=r["timestamp"],open=float(r["open"]),high=float(r["high"]),low=float(r["low"]),close=float(r["close"]),volume=float(r["volume"])) for r in csv.DictReader(f)]
  if len(rows)>=200:out[path.stem]={r["timestamp"]:r for r in rows}
 if not out:raise ValueError("No historical candle CSV files found")
 return out

def signal(history,params):
 if len(history)<max(2200,params["slow"]+288):return None
 c=[r["close"] for r in history]
 fast=statistics.fmean(c[-params["fast"]:])
 slow=statistics.fmean(c[-params["slow"]:])
 prev=statistics.fmean(c[-params["slow"]-288:-288])
 returns=[math.log(c[i]/c[i-1]) for i in range(-576,0)]
 sigma=statistics.pstdev(returns)*math.sqrt(288)
 trend_strength=(slow/prev-1) if prev else 0
 momentum=c[-1]/c[-1-params["momentum"]]-1
 if sigma>0.12:regime="extreme"
 elif fast>slow and trend_strength>0:regime="bull"
 elif fast<slow and trend_strength<0:regime="bear"
 else:regime="sideways"
 if regime!="bull" or momentum<params["threshold"]:return regime,None
 atr=statistics.fmean(max(r["high"]-r["low"],abs(r["high"]-p["close"]),abs(r["low"]-p["close"])) for p,r in zip(history[-289:-1],history[-288:]))
 return regime,{"distance":max(0.012,min(0.05,params["stop"]*atr/c[-1])),"score":momentum/max(sigma,0.001)}

def simulate(data,params,start,end,initial=INITIAL):
 times=sorted(set().union(*(set(p) for p in data.values())))
 history=defaultdict(list);pending={};positions={};cash=initial;peak=initial;max_dd=0
 ledger=[];equity_curve=[];regimes=defaultdict(int);daily_start=initial;day=None;halt=False
 for t in times:
  bars={s:rows[t] for s,rows in data.items() if t in rows}
  active=start<=t<end
  if day!=t[:10]:
   day=t[:10];daily_start=cash+sum(p["qty"]*bars[s]["open"] for s,p in positions.items() if s in bars);halt=False
  # Pending decisions were made using only candles closed before this timestamp.
  for s,order in list(pending.items()):
   if s in bars and active and not halt and s not in positions:
    px=bars[s]["open"]*(1+HALF_SPREAD+SLIPPAGE)
    equity=cash+sum(p["qty"]*bars[k]["open"] for k,p in positions.items() if k in bars)
    allocation=min(cash,0.2*equity,max(0,equity)*0.005/(order["distance"]+ROUND_TRIP))
    if allocation>=5 and len(positions)<3:
     qty=allocation/(px*(1+FEE))
     cash-=allocation
     positions[s]={"entry_time":t,"entry":px,"qty":qty,"entry_cost":allocation,"stop":px*(1-order["distance"]),"target":px*(1+order["distance"]*params["reward"]),"regime":order["regime"],"age":0}
   pending.pop(s,None)
  for s,p in list(positions.items()):
   if s not in bars:continue
   b=bars[s];p["age"]+=1
   reason=None;raw=None
   if b["open"]<=p["stop"]:reason="gap_stop";raw=b["open"]
   elif b["open"]>=p["target"]:reason="gap_target";raw=b["open"]
   elif b["low"]<=p["stop"]:reason="stop";raw=p["stop"]
   elif b["high"]>=p["target"]:reason="target";raw=p["target"]
   elif p["age"]>=864 or t==times[-1] or (active and t>=end):reason="timeout";raw=b["close"]
   if reason:
    exit_px=raw*(1-HALF_SPREAD-SLIPPAGE)
    proceeds=p["qty"]*exit_px*(1-FEE)
    cash+=proceeds
    ledger.append(dict(symbol=s,entry_time=p["entry_time"],exit_time=t,entry_price=p["entry"],exit_price=exit_px,quantity=p["qty"],entry_cost=p["entry_cost"],proceeds=proceeds,net_pnl=proceeds-p["entry_cost"],return_pct=100*(proceeds/p["entry_cost"]-1),reason=reason,regime=p["regime"],fees_estimate=p["entry_cost"]*FEE/(1+FEE)+p["qty"]*exit_px*FEE))
    del positions[s]
  equity=cash+sum(p["qty"]*bars[s]["close"] for s,p in positions.items() if s in bars)
  if active and equity<daily_start*0.98:halt=True
  if active:
   peak=max(peak,equity);max_dd=max(max_dd,1-equity/peak)
   equity_curve.append({"timestamp":t,"equity":round(equity,6)})
  # The candle is added only after fills and risk checks.
  for s,b in bars.items():
   history[s].append(b)
   if len(history[s])>2500:history[s].pop(0)
  if active and not halt and t<end:
   candidates=[]
   for s in bars:
    if s in positions or s in pending:continue
    regime,order=signal(history[s],params)
    if regime:regimes[regime]+=1
    if order:candidates.append((order["score"],s,order,regime))
   for _,s,order,regime in sorted(candidates,reverse=True)[:max(0,3-len(positions))]:
    pending[s]=dict(order,regime=regime)
 # No look-ahead at split: force liquidation at last observed close in window.
 if positions and equity_curve:
  final_t=equity_curve[-1]["timestamp"]
  for s,p in list(positions.items()):
   b=data[s].get(final_t)
   if not b:continue
   exit_px=b["close"]*(1-HALF_SPREAD-SLIPPAGE)
   proceeds=p["qty"]*exit_px*(1-FEE);cash+=proceeds
   ledger.append(dict(symbol=s,entry_time=p["entry_time"],exit_time=final_t,entry_price=p["entry"],exit_price=exit_px,quantity=p["qty"],entry_cost=p["entry_cost"],proceeds=proceeds,net_pnl=proceeds-p["entry_cost"],return_pct=100*(proceeds/p["entry_cost"]-1),reason="window_end",regime=p["regime"],fees_estimate=p["entry_cost"]*FEE/(1+FEE)+p["qty"]*exit_px*FEE))
   del positions[s]
 final=cash
 wins=sum(x["net_pnl"]>0 for x in ledger)
 return {"initial":initial,"final":round(final,4),"return_pct":round(100*(final/initial-1),4),"max_drawdown_pct":round(max_dd*100,4),"trades":len(ledger),"win_rate":round(wins/len(ledger),4) if ledger else None,"regimes":dict(regimes),"ledger":ledger,"equity_curve":equity_curve}

def validate(data):
 times=sorted(set().union(*(set(p) for p in data.values())))
 if len(times)<288*75:raise ValueError("Need at least 75 days of hourly data")
 # Fixed expanding training and successive disjoint 15-day out-of-sample windows.
 windows=[];step=288*15;first=max(288*45,len(times)-3*step)
 for idx in range(first,len(times)-1,step):
  if idx+step>len(times):break
  start,end=times[idx],times[idx+step]
  train_start=times[0];train_end=start
  scores=[]
  for p in PARAMETERS:
   r=simulate(data,p,train_start,train_end)
   scores.append((r["return_pct"]-0.5*r["max_drawdown_pct"],p))
  chosen=max(scores,key=lambda v:v[0])[1]
  result=simulate(data,chosen,start,end)
  windows.append({"start":start,"end":end,"parameters":chosen,"training_score":round(max(v[0] for v in scores),4),"result":result})
 if not windows:raise ValueError("Insufficient bars for out-of-sample windows")
 return {"method":"expanding training, non-overlapping 15-day holdouts; no future candles in signal","execution":"next-bar open; spread, slippage and fees; pessimistic stop-first on ambiguous OHLC bars","windows":windows,"aggregate_oos_return_pct":round(100*(math.prod(w["result"]["final"]/INITIAL for w in windows)-1),4),"note":"Research only. No order-book depth, partial exchange fills, funding or live execution modeled."}

def main():
 report=validate(load_data())
 folder=Path("crypto-agent");folder.mkdir(exist_ok=True)
 (folder/"audit_v2.json").write_text(json.dumps(report,indent=2))
 with (folder/"trades_v2.csv").open("w",newline="") as f:
  fields=["window","symbol","entry_time","exit_time","entry_price","exit_price","quantity","entry_cost","proceeds","net_pnl","return_pct","reason","regime","fees_estimate"]
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
  for i,w in enumerate(report["windows"]):
   for trade in w["result"]["ledger"]:writer.writerow({"window":i+1,**trade})
 print(json.dumps({"windows":len(report["windows"]),"aggregate_oos_return_pct":report["aggregate_oos_return_pct"],"trades":sum(w["result"]["trades"] for w in report["windows"])},indent=2))
if __name__=="__main__":main()
