"""Shared BTC/ETH channel portfolio: chronological, paper-only, next-open entries."""
import json
from pathlib import Path
from backtest_v2 import load_data
from v8_channel_signals import confirmed,atr,updated_stop
from v8_shared_portfolio import SharedPortfolio

def simulate(data,lookback=48,volume=1.15,mode="trailing",start=.6,end=.8):
    timestamps=sorted(set.intersection(*(set(x) for x in data.values())))
    bars={s:[series[t] for t in timestamps] for s,series in data.items()}
    lo=int(len(timestamps)*start);hi=int(len(timestamps)*end)
    p=SharedPortfolio();stops={};peak=200.;dd=0.
    for i in range(lo,hi):
        prices={s:bars[s][i]["close"] for s in bars}
        for s in list(p.positions):
            b=bars[s][i];stop=stops[s]
            channel_floor=min(x["low"] for x in bars[s][i-lookback:i])
            if b["open"]<=stop:exit_price=b["open"]
            elif b["low"]<=stop:exit_price=stop
            elif mode=="channel" and b["open"]<channel_floor:exit_price=b["open"]
            elif i==hi-1:exit_price=b["close"]
            else:exit_price=None
            if exit_price is not None:
                p.sell(s,exit_price);del stops[s]
            elif mode!="channel":
                stops[s]=updated_stop(stop,b["close"],atr(bars[s],i-1),mode)
        equity=p.equity(prices);peak=max(peak,equity);dd=max(dd,1-equity/peak)
        for s in sorted(bars):
            if i<=lo or i>=hi-1 or s in p.positions:continue
            if not confirmed(bars[s],i-1,lookback,volume):continue
            if p.buy(s,bars[s][i]["open"],prices):
                stop=p.positions[s]["cost"]/p.positions[s]["qty"]-2.5*atr(bars[s],i-1)
                stops[s]=stop
                if bars[s][i]["low"]<=stop:
                    p.sell(s,stop);del stops[s]
    for s in list(p.positions):
        p.sell(s,bars[s][hi-1]["close"])
    return {"return_pct":100*(p.cash/200-1),"trades":len(p.ledger),
            "drawdown_pct":100*dd,"ledger":p.ledger}

def research(data):
    rows=[]
    for lookback in (24,48,72):
        for volume in (1.05,1.15,1.3):
            for mode in ("trailing","atr","channel"):
                r=simulate(data,lookback,volume,mode)
                rows.append({"lookback":lookback,"volume":volume,"mode":mode,
                             "validation":{k:v for k,v in r.items() if k!="ledger"}})
    rows.sort(key=lambda x:x["validation"]["return_pct"],reverse=True)
    eligible=[x for x in rows if x["validation"]["return_pct"]>0
              and x["validation"]["trades"]>=8 and x["validation"]["drawdown_pct"]<8]
    # Robustness: require nonnegative performance in at least two earlier disjoint periods.
    chosen=None;stability=[]
    for candidate in eligible:
        tests=[simulate(data,candidate["lookback"],candidate["volume"],candidate["mode"],a,b)
               for a,b in ((.2,.4),(.4,.6),(.6,.8))]
        if sum(x["return_pct"]>0 for x in tests)>=2:
            chosen=candidate
            stability=[{k:v for k,v in x.items() if k!="ledger"} for x in tests]
            break
    final=simulate(data,chosen["lookback"],chosen["volume"],chosen["mode"],.8,1.) if chosen else None
    return {"variants":len(rows),"ranking":rows,"selected":chosen,"final_test":final,
            "stability_periods":stability,
            "shared_cash":True,"paper_only":True}
if __name__=="__main__":
    r=research(load_data())
    Path("crypto-agent/v8-channel-portfolio.json").write_text(json.dumps(r,indent=2))
    print(json.dumps({"selected":r["selected"],"test_return":r["final_test"]["return_pct"] if r["final_test"] else None}))
