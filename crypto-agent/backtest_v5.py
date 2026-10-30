"""V5 end-to-end offline backtest using the same Portfolio and paper_fill engine."""
import csv,json
from pathlib import Path
from engine_v5 import Portfolio
from paper_v5 import paper_fill,MarketConditions
from specialists_v5 import specialists
from backtest_v2 import load_data

def run(data,start=None,end=None,initial=200.,conditions=MarketConditions(),hold_bars=36):
    times=sorted(set().union(*(set(series) for series in data.values())))
    if not times:raise ValueError("No bars")
    start=start or times[0];end=end or times[-1]
    p=Portfolio(initial);history={s:[] for s in data}
    exits={};curve=[];signals=[];last={}
    for t in times:
        if t>=end:break
        bars={s:series[t] for s,series in data.items() if t in series}
        for s,b in bars.items():
            last[s]=b["close"]
        if t>=start:
            for oid,o in list(p.orders.items()):
                if o.status!="open" or o.symbol not in bars:continue
                if o.side=="buy" and oid not in exits:continue
                paper_fill(p,oid,bars[o.symbol],conditions)
            for s,deadline in list(exits.items()):
                if t>=deadline and p.positions.get(s,0)>1e-10:
                    # Cancel any residual buy before liquidating.
                    for oid,o in list(p.orders.items()):
                        if o.symbol==s and o.side=="buy" and o.status=="open":p.cancel(oid)
                    sell_id=f"sell:{s}:{t}"
                    if not any(o.symbol==s and o.side=="sell" and o.status=="open" for o in p.orders.values()):
                        p.place(sell_id,s,"sell",p.available_quantity(s))
                    if s in bars:paper_fill(p,sell_id,bars[s],conditions)
                if p.positions.get(s,0)<=1e-10 and t>=deadline:del exits[s]
            p.reconcile(last)
            curve.append({"timestamp":t,"equity":p.equity(last)})
        for s,b in bars.items():
            history[s].append(b)
            if len(history[s])>2500:history[s].pop(0)
        if t<start:continue
        for s in bars:
            if s in exits or p.positions.get(s,0)>1e-10 or any(o.symbol==s and o.status=="open" for o in p.orders.values()):continue
            choices=specialists(history[s])
            if not choices:continue
            choice=max(choices,key=lambda x:x["score"])
            # Risk-limited 10% allocation, no leverage or shorting.
            notional=min(p.cash*.1,20.)
            if notional<5:continue
            quantity=notional/(bars[s]["close"]*(1+conditions.fee+conditions.spread/2+conditions.slippage))
            oid=f"buy:{s}:{t}"
            p.place(oid,s,"buy",quantity)
            signals.append({"timestamp":t,"symbol":s,**choice})
            # Exit after at least hold_bars global 5-minute steps.
            idx=times.index(t)
            exits[s]=times[min(idx+hold_bars,len(times)-1)]
    # Mark-to-market at end; do not invent final liquidation.
    return {"initial":initial,"final_equity":p.equity(last),"realized_pnl":p.realized_pnl,
            "fees":p.fees_paid,"fills":len(p.fills),"signals":len(signals),
            "open_positions":{s:q for s,q in p.positions.items() if q>1e-10},
            "equity_curve":curve,"ledger":[vars(f) for f in p.fills],
            "model":"V5 offline execution foundation, untrained specialists"}

def main():
    result=run(load_data())
    out=Path("crypto-agent")
    (out/"audit_v5.json").write_text(json.dumps({k:v for k,v in result.items() if k not in ("ledger","equity_curve")},indent=2))
    with (out/"fills_v5.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["order_id","symbol","side","quantity","price","fee"])
        writer.writeheader();writer.writerows(result["ledger"])
    print(json.dumps({k:v for k,v in result.items() if k not in ("ledger","equity_curve")},indent=2))
if __name__=="__main__":main()
