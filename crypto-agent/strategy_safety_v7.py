"""Research safety gates inspired by Freqtrade and NautilusTrader.
No future bar may affect a historical entry signal. Portfolio promotion is separate.
"""
import math
from statistics import mean

def prefix_invariance(signal_fn,bars,indices):
    failures=[]
    for i in indices:
        if i>=len(bars) or i<1:continue
        past=signal_fn(bars[:i+1],i)
        future=signal_fn(bars,i)
        if past!=future:failures.append(i)
    return {"passed":not failures,"failures":failures}

def risk_report(result,minimum_trades=10,max_drawdown_pct=12.):
    reasons=[]
    if result["trades"]<minimum_trades:reasons.append("insufficient_trades")
    if result["return_pct"]<=0:reasons.append("nonpositive_net_return")
    if result["max_drawdown_pct"]>max_drawdown_pct:reasons.append("excessive_drawdown")
    return {"eligible":not reasons,"reasons":reasons}

def choose_with_validation(tournament_report):
    # The untouched test set is never read here.
    ranking=tournament_report["ranking"]
    assets=tournament_report["per_asset"]
    for candidate in ranking:
        name=candidate["strategy"]
        if name=="cash" or candidate["validation_mean_return_pct"]<=0:continue
        validation=[x[name]["validation"] for x in assets.values()]
        if sum(r["trades"] for r in validation)<10:continue
        if any(not risk_report(r,minimum_trades=1)["eligible"] for r in validation):continue
        return {"candidate":name,"reason":"passed_validation_risk_gate"}
    return {"candidate":None,"reason":"cash_beats_unvalidated_strategies"}
