"""CryptoAgent V4 research: chronological calibration and strict out-of-sample evaluation.
No live orders. Parameters learned exclusively from completed training trades.
"""
import csv
import json
import math
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from backtest_v2 import load_data
from backtest_v3 import run
from strategy_v3 import Config

INITIAL=200.0
BAR_DAY=288
TRAIN_DAYS=45
TEST_DAYS=15
MIN_TRADES=8

def calibrate(ledger):
    grouped=defaultdict(list)
    for trade in ledger:
        grouped[trade["strategy"]].append(trade)
    priors=[]
    selected=[]
    stats={}
    for name in ("trend","breakout","mean_reversion"):
        rows=grouped[name]
        wins=sum(t["pnl"]>0 for t in rows)
        pnl=sum(t["pnl"] for t in rows)
        # Shrink noisy win rates toward a conservative 35% baseline.
        probability=(wins+7)/(len(rows)+20)
        stats[name]={"trades":len(rows),"wins":wins,"net_pnl":round(pnl,6),
                     "win_rate":round(wins/len(rows),4) if rows else None,
                     "calibrated_probability":round(probability,6)}
        if len(rows)>=MIN_TRADES and pnl>0:
            selected.append(name)
            priors.append((name,probability))
    return tuple(selected),tuple(priors),stats

def benchmark(data,start,end):
    results={}
    for symbol in ("BTCUSDT","ETHUSDT"):
        series=data.get(symbol,{})
        candles=[bar for t,bar in series.items() if start<=t<end]
        if len(candles)<2:
            results[symbol]=None
        else:
            results[symbol]=100*(candles[-1]["close"]/candles[0]["open"]-1)
    return results

def summarize(result):
    rows=result["ledger"]
    wins=[t["pnl"] for t in rows if t["pnl"]>0]
    losses=[-t["pnl"] for t in rows if t["pnl"]<0]
    return {"final":round(result["final"],6),
            "return_pct":round(result["return_pct"],6),
            "max_drawdown_pct":round(result["max_drawdown_pct"],6),
            "trades":len(rows),
            "win_rate":round(len(wins)/len(rows),5) if rows else None,
            "profit_factor":round(sum(wins)/sum(losses),5) if losses else None,
            "net_pnl":round(sum(t["pnl"] for t in rows),6)}

def validate(data):
    times=sorted(set().union(*(set(series) for series in data.values())))
    if len(times)<BAR_DAY*(TRAIN_DAYS+TEST_DAYS):
        raise ValueError("Need at least 60 complete days of 5m history")
    step=BAR_DAY*TEST_DAYS
    first=BAR_DAY*TRAIN_DAYS
    windows=[]
    trades=[]
    # Expanding training history; only completed training trades can calibrate.
    for index in range(first,len(times)-step+1,step):
        start,end=times[index],times[index+step-1]
        training=run(data,times[0],start)
        enabled,priors,training_stats=calibrate(training["ledger"])
        config=replace(Config(),enabled_strategies=enabled,learned_priors=priors)
        # With no demonstrated edge, preserve cash rather than force trades.
        test=run(data,start,end,config)
        windows.append({"train_start":times[0],"train_end_exclusive":start,
                        "test_start":start,"test_end_inclusive":end,
                        "selected_strategies":list(enabled),"training":training_stats,
                        "oos":summarize(test),"benchmarks":benchmark(data,start,end)})
        for trade in test["ledger"]:
            trades.append({"fold":len(windows),**trade})
    if not windows:
        raise ValueError("No complete out-of-sample windows")
    compounded=100*(math.prod(1+w["oos"]["return_pct"]/100 for w in windows)-1)
    return {"version":"V4 research, training-only empirical calibration",
            "training":"expanding 45+ days, 15-day disjoint test windows",
            "execution":"next 5m open, fees, fixed spread and slippage, conservative OHLC stop priority",
            "aggregate_oos_return_pct":round(compounded,6),
            "windows":windows,
            "limitations":["Not trained ML","No L2 book or genuine partial fills",
                           "No real historical spread, market impact or funding",
                           "No short selling or leverage","Small training sample may prevent trading"],
            "trades":trades}

def main():
    report=validate(load_data())
    folder=Path("crypto-agent")
    folder.mkdir(exist_ok=True)
    trades=report.pop("trades")
    (folder/"audit_v4.json").write_text(json.dumps(report,indent=2))
    columns=["fold","symbol","strategy","regime","entry_time","exit_time",
             "entry","exit","quantity","cost","proceeds","pnl","reason"]
    with (folder/"trades_v4.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trades)
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
