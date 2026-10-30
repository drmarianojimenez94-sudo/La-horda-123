"""Research-only leverage policy. Never authorizes exchange orders.
Leverage is gated by independent validation and adverse execution stress.
"""
from math import isfinite

def leverage_decision(validation,requested=2.0,fee_per_side=.001,
                      funding_rate=.0003,stress_move=.08,
                      max_leverage=2.0,max_stress_loss=.10):
    trades=int(validation.get("trades",0))
    ret=float(validation.get("return_pct",0))/100
    dd=float(validation.get("max_drawdown_pct",100))/100
    if not all(isfinite(x) for x in (ret,dd,requested,stress_move)):
        return {"approved":False,"leverage":1.0,"reason":"invalid_metrics"}
    if trades<30:return {"approved":False,"leverage":1.0,"reason":"insufficient_validation_trades"}
    if ret<=0:return {"approved":False,"leverage":1.0,"reason":"nonpositive_validation_return"}
    if dd>.06:return {"approved":False,"leverage":1.0,"reason":"excessive_validation_drawdown"}
    if not 1<requested<=max_leverage:
        return {"approved":False,"leverage":1.0,"reason":"leverage_outside_limit"}
    # Adverse movement plus round-trip fees, funding and execution uncertainty.
    stressed_loss=requested*(stress_move+2*fee_per_side+funding_rate+.002)
    if stressed_loss>max_stress_loss:
        return {"approved":False,"leverage":1.0,"reason":"adverse_stress_exceeds_budget",
                "stress_loss_fraction":stressed_loss}
    return {"approved":True,"leverage":requested,"reason":"validation_and_stress_passed",
            "stress_loss_fraction":stressed_loss,
            "paper_only":True}

def leverage_scenarios(validation,levels=(1.,1.25,1.5,2.)):
    return [{"requested":level,**leverage_decision(validation,requested=level)}
            for level in levels]
