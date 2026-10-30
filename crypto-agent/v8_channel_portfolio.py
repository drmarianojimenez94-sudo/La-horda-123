"""Shared BTC/ETH channel portfolio: chronological, paper-only, next-open entries."""
import json
from pathlib import Path
from backtest_v2 import load_data
from v8_channel_signals import confirmed,atr,updated_stop
from v8_shared_portfolio import SharedPortfolio
from statistics import mean

def simulate(data,lookback=48,volume=1.15,mode="trailing",start=.6,end=.8,
             confirm_bars=1,risk_fraction=.005,max_portfolio_risk=.015,drawdown_halt=.08):
    timestamps=sorted(set.intersection(*(set(x) for x in data.values())))
    bars={s:[series[t] for t in timestamps] for s,series in data.items()}
    lo=int(len(timestamps)*start);hi=int(len(timestamps)*end)
    p=SharedPortfolio();stops={};peak=200.;dd=0.;halted=False;rejections={}
    def reject(reason):rejections[reason]=rejections.get(reason,0)+1
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
        if dd>=drawdown_halt:halted=True
        for s in sorted(bars):
            if halted or i<=lo or i>=hi-1 or s in p.positions:continue
            signal_i=i-1-confirm_bars
            if signal_i<lo or not confirmed(bars[s],signal_i,lookback,volume):continue
            level=max(x["high"] for x in bars[s][signal_i-lookback:signal_i])
            follow=bars[s][signal_i+1:i]
            if any(x["close"]<level or x["low"]<level-.5*atr(bars[s],signal_i) for x in follow):
                reject("failed_retest");continue
            entry=bars[s][i]["open"]*1.0008
            distance=2.5*atr(bars[s],i-1)
            if distance<=0:reject("invalid_atr");continue
            active_risk=sum(p.positions[x]["qty"]*max(0.,prices[x]-stops[x]) for x in p.positions)
            risk_budget=min(equity*risk_fraction,max(0.,equity*max_portfolio_risk-active_risk))
            if risk_budget<1e-8:reject("portfolio_risk_cap");continue
            max_notional=min(20.,risk_budget*entry/distance)
            if p.buy(s,bars[s][i]["open"],prices,max_notional=max_notional):
                stop=entry-distance
                stops[s]=stop
                if bars[s][i]["low"]<=stop:
                    p.sell(s,stop);del stops[s]
    for s in list(p.positions):
        p.sell(s,bars[s][hi-1]["close"])
    return {"return_pct":100*(p.cash/200-1),"trades":len(p.ledger),
            "drawdown_pct":100*dd,"ledger":p.ledger,"halted":halted,
            "rejections":rejections,"fees":p.fees}

def research(data):
    rows=[]
    # Four nonoverlapping development periods; final 20% is untouched.
    development=((0.,.2),(.2,.4),(.4,.6),(.6,.8))
    for lookback in (24,48,72):
        for volume in (1.05,1.15,1.3):
            for mode in ("trailing","atr","channel"):
                folds=[simulate(data,lookback,volume,mode,a,b) for a,b in development]
                avg=mean(x["return_pct"] for x in folds)
                positives=sum(x["return_pct"]>0 for x in folds)
                trades=sum(x["trades"] for x in folds)
                rows.append({"lookback":lookback,"volume":volume,"mode":mode,
                             "development_mean_pct":avg,"positive_folds":positives,
                             "development_trades":trades,
                             "development_folds":[{k:v for k,v in f.items() if k!="ledger"} for f in folds]})
    rows.sort(key=lambda x:x["development_mean_pct"],reverse=True)
    eligible=[x for x in rows if x["development_mean_pct"]>0
              and x["positive_folds"]>=3 and x["development_trades"]>=12
              and all(f["drawdown_pct"]<8 for f in x["development_folds"])]
    chosen=eligible[0] if eligible else None
    final=simulate(data,chosen["lookback"],chosen["volume"],chosen["mode"],.8,1.) if chosen else None
    return {"variants":len(rows),"ranking":rows,"selected":chosen,"final_test":final,
            "development_windows":development,"final_window":(.8,1.),
            "shared_cash":True,"paper_only":True}

if __name__=="__main__":
    r=research(load_data())
    Path("crypto-agent/v8-channel-portfolio.json").write_text(json.dumps(r,indent=2))
    print(json.dumps({"selected":r["selected"],"test_return":r["final_test"]["return_pct"] if r["final_test"] else None}))
