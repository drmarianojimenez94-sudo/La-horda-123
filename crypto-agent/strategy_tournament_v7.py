"""Causal, cost-aware strategy tournament; research only.
Each candidate is simulated on the same 5-minute OHLCV bars with next-open entries,
conservative stop-first OHLC exits, fees, spread and slippage. No future information
enters a signal. Never select parameters based on the final holdout.
"""
import json,math
from statistics import mean,pstdev
from pathlib import Path
from backtest_v2 import load_data
from strategy_safety_v7 import choose_with_validation,prefix_invariance

FEE=.001
FRICTION=.0008
PARAMS={
 "trend_pullback":{"stop":.012,"take":.024,"max_bars":72},
 "breakout_retest":{"stop":.012,"take":.03,"max_bars":96},
 "volatility_breakout":{"stop":.016,"take":.032,"max_bars":72},
 "mean_reversion":{"stop":.012,"take":.018,"max_bars":48},
 "cash":{"stop":0,"take":0,"max_bars":0},
}
def signals(bars,i):
    if i<120:return []
    close=[float(x["close"]) for x in bars[i-120:i+1]]
    price=close[-1]
    if price<=0:return []
    ma24=mean(close[-24:]);ma96=mean(close[-96:])
    prev=close[-13]
    returns=[close[k]/close[k-1]-1 for k in range(1,len(close))]
    vol=pstdev(returns[-48:])
    if not 0.00005<vol<.02:return []
    v=float(bars[i]["volume"])
    avgvol=mean(float(x["volume"]) for x in bars[i-48:i])
    rv=v/max(avgvol,1e-12)
    high=max(float(x["high"]) for x in bars[i-48:i])
    low=min(float(x["low"]) for x in bars[i-48:i])
    out=[]
    if ma24>ma96*1.002 and prev>ma24 and price<=ma24*1.002 and price>=ma96:
        out.append("trend_pullback")
    if ma24>ma96 and price>high and rv>=1.5:
        out.append("volatility_breakout")
    if ma24>ma96 and max(close[-13:-1])>max(close[-62:-14]) and price>max(close[-62:-14]) and rv>1.1:
        out.append("breakout_retest")
    z=(price-mean(close[-48:]))/max(pstdev(close[-48:]),1e-12)
    if z< -2 and ma24>=ma96*.995 and price>low:
        out.append("mean_reversion")
    return out

def simulate(bars,name,start,end,initial=200):
    if name=="cash":return {"return_pct":0.,"trades":0,"fees":0.,"win_rate":None,"max_drawdown_pct":0.}
    cfg=PARAMS[name]
    cash=float(initial);position=None;trades=0;wins=0;fees=0.;peak=cash;dd=0.
    # start/end are bar indices; warmup is strictly earlier than start.
    for i in range(start,min(end,len(bars))):
        bar=bars[i]
        if position:
            entry,qty,stop,target,deadline,cost=position
            op=float(bar["open"]);hi=float(bar["high"]);lo=float(bar["low"])
            if op<=stop:exit_price=op
            elif op>=target:exit_price=op
            elif lo<=stop:exit_price=stop
            elif hi>=target:exit_price=target
            elif i>=deadline or i==end-1:exit_price=float(bar["close"])
            else:exit_price=None
            if exit_price is not None:
                px=exit_price*(1-FRICTION)
                gross=qty*px
                fee=gross*FEE
                cash+=gross-fee;fees+=fee
                wins+=int(gross-fee>cost)
                trades+=1;position=None
        equity=cash+(position[1]*float(bar["close"]) if position else 0)
        peak=max(peak,equity);dd=max(dd,1-equity/peak)
        # Signals at previous candle close; enter at this candle open.
        if position is None and i>start and i>120 and name in signals(bars,i-1):
            allocation=min(20.,cash*.1)
            px=float(bar["open"])*(1+FRICTION)
            if allocation>=5 and px>0:
                qty=allocation/(px*(1+FEE))
                entry_fee=qty*px*FEE
                cash-=allocation;fees+=entry_fee
                position=(px,qty,px*(1-cfg["stop"]),px*(1+cfg["take"]),
                          i+cfg["max_bars"],allocation)
    # The last bar forces a conservative close at its close if a position remains.
    if position:
        px=float(bars[min(end,len(bars))-1]["close"])*(1-FRICTION)
        gross=position[1]*px;fee=gross*FEE
        cash+=gross-fee;fees+=fee
        wins+=int(gross-fee>position[5]);trades+=1
    return {"return_pct":100*(cash/initial-1),"trades":trades,
            "fees":fees,"win_rate":wins/trades if trades else None,
            "max_drawdown_pct":dd*100}

def tournament(data,train_fraction=.6,validation_fraction=.2):
    results={}
    for symbol,series in data.items():
        bars=[series[t] for t in sorted(series)]
        n=len(bars);a=int(n*train_fraction);b=int(n*(train_fraction+validation_fraction))
        if a<150 or b>=n:continue
        results[symbol]={}
        for name in PARAMS:
            results[symbol][name]={
                "train":simulate(bars,name,120,a),
                "validation":simulate(bars,name,a,b),
                "test":simulate(bars,name,b,n)}
    ranking=[]
    for name in PARAMS:
        vals=[x[name]["validation"] for x in results.values()]
        if not vals:continue
        avg=sum(v["return_pct"] for v in vals)/len(vals)
        count=sum(v["trades"] for v in vals)
        ranking.append({"strategy":name,"validation_mean_return_pct":avg,
                        "validation_trades":count})
    ranking.sort(key=lambda r:r["validation_mean_return_pct"],reverse=True)
    # Select only with validation, never test. Do not declare a champion if cash wins.
    winner=next((r["strategy"] for r in ranking if r["strategy"]!="cash"
                 and r["validation_mean_return_pct"]>0 and r["validation_trades"]>=10),None)
    checks={symbol:prefix_invariance(signals,[series[t] for t in sorted(series)],
                 [120,160,200,250]) for symbol,series in data.items()}
    return {"lookahead_checks":checks,"source":"real_5m_ohlcv","execution":"next_open_with_fees_spread_slippage",
            "selection_only_on_validation":True,"selected_candidate":winner,
            "ranking":ranking,"per_asset":results,
            "test_is_report_only":True,"profitability_guaranteed":False}

if __name__=="__main__":
    result=tournament(load_data())
    result["validation_risk_selection"]=choose_with_validation(result)
    path=Path("crypto-agent/strategy_tournament_v7.json")
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps({"selected_candidate":result["selected_candidate"],"ranking":result["ranking"]},indent=2))
