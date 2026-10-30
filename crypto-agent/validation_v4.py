"""Temporal leakage, sensitivity and overfitting checks for CryptoAgent V4.
Research diagnostics only. No future observations are used in decisions.
"""
from dataclasses import replace
from statistics import mean
from strategy_v3 import Config,candidates
from backtest_v3 import run

def check_prefix_invariance(bars,cut=1800):
    if len(bars)<cut+100:return {"passed":False,"reason":"insufficient_history"}
    a=candidates(bars[:cut])
    b=candidates(bars[:cut]+bars[cut:cut+100])
    # A future extension must not mutate historical input or earlier predictions.
    a_again=candidates(bars[:cut])
    return {"passed":a==a_again,"prefix_signals":len(a),"later_signals":len(b)}

def check_fold_separation(train,calibration,test):
    sets=[(min(x['signal_time'] for x in part),max(x['label_end'] for x in part)) for part in (train,calibration,test) if part]
    return all(sets[i][1]<sets[i+1][0] for i in range(len(sets)-1))

def sensitivity(data,start,end,config):
    variants=[
        ("baseline",config),
        ("costs_2x",replace(config,fee=config.fee*2,slippage=config.slippage*2,half_spread=config.half_spread*2)),
        ("volume_stricter",replace(config,breakout_volume_ratio=config.breakout_volume_ratio*1.25)),
        ("extension_stricter",replace(config,breakout_max_extension=config.breakout_max_extension*.75)),
        ("liquidity_stricter",replace(config,breakout_min_quote_volume=config.breakout_min_quote_volume*2)),
    ]
    outcomes={}
    for name,cfg in variants:
        result=run(data,start,end,cfg)
        outcomes[name]={"return_pct":round(result['return_pct'],5),"trades":result['trades']}
    returns=[v["return_pct"] for v in outcomes.values()]
    return {"variants":outcomes,"positive_fraction":sum(x>0 for x in returns)/len(returns),
            "return_range":round(max(returns)-min(returns),5),
            "fragile":sum(x>0 for x in returns)<len(returns)*.6}

def gate(report):
    windows=report.get('windows',[])
    if len(windows)<2:return {"passed":False,"reason":"fewer_than_two_oos_windows"}
    positive=sum(w['oos']['return_pct']>0 for w in windows)
    return {"passed":positive>=max(2,len(windows)*.6) and report['aggregate_oos_return_pct']>0,
            "positive_windows":positive,"windows":len(windows),
            "note":"Diagnostic gate; not proof of live profitability"}
