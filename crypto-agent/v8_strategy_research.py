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
from v8_unified_ledger import UnifiedSpotLedger
from v9_diagnostics import trade_attribution, classify_regime, regime_validation, causal_prior_weights
from v8_run_memory import prior_candidates
import os

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
    """Single-asset research adapter to canonical shared execution ledger."""
    ledger=UnifiedSpotLedger(cash=initial)
    symbol="RESEARCH"
    stop=target=deadline=None
    peak=initial;dd=0.;wins=0;trades=0
    end=min(end,len(bars))
    for i in range(start,end):
        bar=bars[i]
        if symbol in ledger.positions:
            op=bar["open"]
            if op<=stop:raw=op
            elif op>=target:raw=op
            elif bar["low"]<=stop:raw=stop
            elif bar["high"]>=target:raw=target
            elif i>=deadline or i==end-1:raw=bar["close"]
            else:raw=None
            if raw is not None:
                pnl=ledger.sell(symbol,raw,time=i,reason="stop_target_or_timeout")
                trades+=1;wins+=int(pnl>0)
        equity=ledger.equity({symbol:bar["close"]})
        peak=max(peak,equity);dd=max(dd,1-equity/peak)
        if symbol not in ledger.positions and i>start and i<end-1 and signal(bars,i-1,c):
            if ledger.buy(symbol,bar["open"],{symbol:bar["open"]},notional_cap=min(20.,ledger.cash*.1),time=i):
                entry=ledger.positions[symbol]["entry"]
                stop=entry*(1-c["stop"]);target=entry*(1+c["target"])
                deadline=i+c["max_bars"]
                if bar["low"]<=stop or bar["high"]>=target:
                    raw=stop if bar["low"]<=stop else target
                    pnl=ledger.sell(symbol,raw,time=i,reason="entry_candle")
                    trades+=1;wins+=int(pnl>0)
    if symbol in ledger.positions:
        pnl=ledger.sell(symbol,bars[end-1]["close"],time=end-1,reason="window_end")
        trades+=1;wins+=int(pnl>0)
    audit=ledger.reconcile({})
    return {"return_pct":100*(audit["equity"]/initial-1),"trades":trades,
            "win_rate":wins/trades if trades else None,
            "fees":audit["fees"],"max_drawdown_pct":dd*100,
            "reconciled":audit["reconciled"],"attribution":trade_attribution(ledger.journal,initial)}

def evaluate(data, memory_path=None, cutoff_ms=None):
    cutoff_ms = int(os.getenv("TRAIN_CUTOFF_MS","0")) if cutoff_ms is None else cutoff_ms
    memory_path = memory_path or os.getenv("V8_MEMORY_PATH","crypto-agent/state/v8-research.sqlite3")
    past = prior_candidates(memory_path,cutoff_ms) if cutoff_ms>0 else []
    historical = [{"trained_until_ms":p["trained_until_ms"],"ranked":p["validation_top"]} for p in past]
    prior_scores = causal_prior_weights(historical,cutoff_ms) if historical else {}
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
        regimes=[]
        for symbol,series in data.items():
            bars=[series[t] for t in sorted(series)]
            if len(bars)<1000:continue
            a=int(len(bars)*.6);b=int(len(bars)*.8)
            fold_size=max(1,(b-a)//3)
            for start in range(a,b,fold_size):
                end=min(start+fold_size,b)
                if end-start<2:continue
                result=simulate(bars,c,start,end)
                regimes.append({"symbol":symbol,"regime":classify_regime(bars,start),
                                "trades":result["trades"],"net_return_pct":result["return_pct"],
                                "start":start,"end":end})
        grouped=[]
        for regime in ("bull","bear","sideways"):
            subset=[x for x in regimes if x["regime"]==regime]
            if subset:
                grouped.append({"regime":regime,"trades":sum(x["trades"] for x in subset),
                                "net_return_pct":sum(x["net_return_pct"] for x in subset)})
        gate=regime_validation(grouped)
        vals=[r["validation"] for r in asset_results.values()]
        avg=mean(x["return_pct"] for x in vals)
        total=sum(x["trades"] for x in vals)
        dd=max(x["max_drawdown_pct"] for x in vals)
        rows.append({"id":c["id"],"family":c["family"],"params":c,
                     "validation_mean_pct":avg,"validation_trades":total,
                     "validation_max_dd_pct":dd,"per_asset":asset_results,
                     "regime_folds":regimes,"regime_gate":gate,"historical_hint":prior_scores.get(c["id"])})
    ranked=sorted(rows,key=lambda r:r["validation_mean_pct"],reverse=True)
    eligible=[r for r in ranked if r["validation_mean_pct"]>0 and
              r["validation_trades"]>=20 and r["validation_max_dd_pct"]<=12 and r["regime_gate"]["approved"]]
    chosen=eligible[0] if eligible else None
    leverage={symbol:leverage_scenarios(chosen["per_asset"][symbol]["validation"])
              for symbol in chosen["per_asset"]} if chosen else {}
    return {"leverage_research":leverage,"leverage_live_enabled":False,
            "data_type":"real_5m_OHLCV","candidates":len(strategies),
            "tested":len(rows),"selected":chosen["id"] if chosen else None,
            "selection_policy":"validation_only_positive_net_min20_trades_max12pct_dd_and_regime_gate",
            "v9_memory_prior_runs":len(past),"v9_memory_used_for_ranking":bool(prior_scores),
            "v9_memory_used_for_promotion":False,"v9_regime_gate_enabled":True,
            "selected_test_results":chosen["per_asset"] if chosen else None,
            "ranked":ranked,"cash_return_pct":0.0,"real_orders":False,
            "warning":"Multiple-hypothesis search increases overfitting risk; test results are descriptive only."}

if __name__=="__main__":
    report=evaluate(load_data())
    Path("crypto-agent/v8-strategy-research.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({"candidates":report["candidates"],"tested":report["tested"],"selected":report["selected"]},indent=2))
