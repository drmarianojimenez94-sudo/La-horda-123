"""V8 research universe: 50 DISTINCT parameterized hypotheses in five families.
Causal signal at previous completed candle, next-open execution, fee+spread+slippage.
Candidate ranking is validation-only; final test is never used for selection.
These are research hypotheses, NOT 50 independently proven profitable strategies.
"""
import json,math
from pathlib import Path
from statistics import mean,pstdev
from backtest_v2 import load_data
from v8_leverage_policy import leverage_scenarios

FAMILIES=("trend_pullback","channel_breakout","momentum","mean_reversion","volatility_expansion")
COST_PER_SIDE=.0018  # 0.10% fee + 0.03% half-spread + 0.05% slippage
def universe():
    return [{"id":f"{family}-{k:02d}","family":family,
             "fast":12+6*k,"slow":72+12*k,"lookback":24+6*k,
             "volume_min":1+.08*k,"stop":.008+.001*k,
             "target":.014+.002*k,"max_bars":24+6*k}
            for family in FAMILIES for k in range(1,11)]

def signal(bars,i,c):
    if i<max(c["slow"]+2,c["lookback"]+2):return False
    b=bars[i];price=b["close"]
    if price<=0:return False
    recent=bars[i-c["slow"]+1:i+1]
    fast=mean(x["close"] for x in recent[-c["fast"]:])
    slow=mean(x["close"] for x in recent)
    earlier=bars[i-c["lookback"]:i]
    hi=max(x["high"] for x in earlier);lo=min(x["low"] for x in earlier)
    vol=mean(x["volume"] for x in earlier)
    relative=b["volume"]/max(vol,1e-9)
    sd=pstdev(x["close"] for x in earlier)
    z=(price-mean(x["close"] for x in earlier))/max(sd,1e-9)
    family=c["family"]
    if family=="trend_pullback":return fast>slow*1.002 and price<=fast*1.002 and price>=slow
    if family=="channel_breakout":
        from v8_channel_signals import confirmed
        return fast>slow*.998 and confirmed(bars,i,c["lookback"],max(1.05,c["volume_min"]*.9))
    if family=="momentum":return fast>slow and price/earlier[0]["close"]-1>.004+.001*k_from(c) and relative>1
    if family=="mean_reversion":return z<-(1.5+.1*k_from(c)) and fast>=slow*.99
    if family=="volatility_expansion":
        previous=bars[i-2*c["lookback"]:i-c["lookback"]]
        if len(previous)<c["lookback"]:return False
        old=pstdev(x["close"]/max(previous[0]["close"],1e-9) for x in previous)
        new=sd/max(price,1e-9)
        return fast>slow and new>old*(1.1+.05*k_from(c)) and relative>=c["volume_min"]
    return False

def k_from(c):return int(c["id"].split("-")[-1])

def simulate(bars,c,start,end,initial=200.):
    cash=initial;position=None;trades=0;wins=0;fees=0.;peak=initial;dd=0.
    for i in range(start,min(end,len(bars))):
        b=bars[i]
        if position:
            qty,entry_cost,stop,target,deadline=position
            op=b["open"]
            if op<=stop:raw=op
            elif op>=target:raw=op
            elif b["low"]<=stop:raw=stop
            elif b["high"]>=target:raw=target
            elif i>=deadline or i==end-1:raw=b["close"]
            else:raw=None
            if raw is not None:
                px=raw*(1-COST_PER_SIDE+.001)
                proceeds=qty*px*(1-.001)
                fees+=qty*px*.001;cash+=proceeds
                wins+=int(proceeds>entry_cost);trades+=1;position=None
        equity=cash+(position[0]*b["close"] if position else 0)
        peak=max(peak,equity);dd=max(dd,1-equity/peak)
        if position is None and i>start and i<min(end,len(bars))-1 and signal(bars,i-1,c):
            allocation=min(20.,cash*.1)
            px=b["open"]*(1+COST_PER_SIDE-.001)
            if allocation>=5 and px>0:
                qty=allocation/(px*1.001)
                fees+=qty*px*.001;cash-=allocation
                position=(qty,allocation,px*(1-c["stop"]),px*(1+c["target"]),i+c["max_bars"])
                # Entry is at current open: its stop may be hit within the SAME candle.
                # Conservative OHLC assumption: stop takes precedence over target.
                if b["low"]<=position[2] or b["high"]>=position[3]:
                    raw=position[2] if b["low"]<=position[2] else position[3]
                    exit_px=raw*(1-COST_PER_SIDE+.001)
                    proceeds=qty*exit_px*(1-.001)
                    fees+=qty*exit_px*.001
                    cash+=proceeds
                    wins+=int(proceeds>allocation)
                    trades+=1
                    position=None
    if position:
        px=bars[min(end,len(bars))-1]["close"]*(1-COST_PER_SIDE+.001)
        proceeds=position[0]*px*.999
        fees+=position[0]*px*.001;cash+=proceeds
        trades+=1;wins+=int(proceeds>position[1])
    return {"return_pct":100*(cash/initial-1),"trades":trades,"win_rate":wins/trades if trades else None,
            "fees":fees,"max_drawdown_pct":100*dd}

def evaluate(data):
    strategies=universe();rows=[]
    for c in strategies:
        asset_results={}
        for symbol,series in data.items():
            bars=[series[t] for t in sorted(series)]
            if len(bars)<1000:continue
            a=int(len(bars)*.6);b=int(len(bars)*.8)
            asset_results[symbol]={"train":simulate(bars,c,max(c["slow"]+2,200),a),
                                   "validation":simulate(bars,c,a,b),
                                   "test":simulate(bars,c,b,len(bars))}
        if not asset_results:continue
        vals=[r["validation"] for r in asset_results.values()]
        avg=mean(x["return_pct"] for x in vals)
        total=sum(x["trades"] for x in vals)
        dd=max(x["max_drawdown_pct"] for x in vals)
        rows.append({"id":c["id"],"family":c["family"],"params":c,
                     "validation_mean_pct":avg,"validation_trades":total,
                     "validation_max_dd_pct":dd,"per_asset":asset_results})
    ranked=sorted(rows,key=lambda r:r["validation_mean_pct"],reverse=True)
    eligible=[r for r in ranked if r["validation_mean_pct"]>0 and
              r["validation_trades"]>=20 and r["validation_max_dd_pct"]<=12]
    chosen=eligible[0] if eligible else None
    leverage={symbol:leverage_scenarios(chosen["per_asset"][symbol]["validation"])
              for symbol in chosen["per_asset"]} if chosen else {}
    return {"leverage_research":leverage,"leverage_live_enabled":False,
            "data_type":"real_5m_OHLCV","candidates":len(strategies),
            "tested":len(rows),"selected":chosen["id"] if chosen else None,
            "selection_policy":"validation_only_positive_net_min20_trades_max12pct_dd",
            "selected_test_results":chosen["per_asset"] if chosen else None,
            "ranked":ranked,"cash_return_pct":0.0,"real_orders":False,
            "warning":"Multiple-hypothesis search increases overfitting risk; test results are descriptive only."}

if __name__=="__main__":
    report=evaluate(load_data())
    Path("crypto-agent/v8-strategy-research.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({"candidates":report["candidates"],"tested":report["tested"],"selected":report["selected"]},indent=2))
