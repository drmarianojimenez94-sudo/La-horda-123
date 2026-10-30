"""Crypto Agent V3: research-only multi-strategy, multi-timeframe decision engine.
Uses completed 5-minute bars only. No exchange orders or leverage.
"""
import math
import statistics
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    risk_fraction: float = 0.0025
    max_exposure: float = 0.40
    max_positions: int = 3
    max_daily_loss: float = 0.02
    max_drawdown: float = 0.10
    min_expected_net: float = 0.001
    fee: float = 0.001
    half_spread: float = 0.0003
    slippage: float = 0.0005
    learned_priors: tuple = ()
    learned_model: tuple = ()
    calibration_model: tuple = ()
    enabled_strategies: tuple = ("trend", "breakout", "mean_reversion")
    breakout_volume_ratio: float = 1.3
    breakout_max_extension: float = 0.008
    breakout_retest_tolerance: float = 0.004
    breakout_min_quote_volume: float = 100000.0
    breakout_max_range: float = 0.025

def aggregate(bars, n):
    """Build completed higher-timeframe OHLCV bars from chronological 5m candles."""
    full = len(bars) // n
    result = []
    for i in range(full):
        batch = bars[i*n:(i+1)*n]
        result.append(dict(timestamp=batch[-1]["timestamp"],open=batch[0]["open"],
                           high=max(x["high"] for x in batch),
                           low=min(x["low"] for x in batch),
                           close=batch[-1]["close"],
                           volume=sum(x["volume"] for x in batch)))
    return result

def classify(bars):
    """Regime from completed 4h candles (48 five-minute bars each)."""
    h4 = aggregate(bars,48)
    if len(h4)<36:return "unknown"
    closes=[b["close"] for b in h4]
    fast=statistics.fmean(closes[-8:])
    slow=statistics.fmean(closes[-32:])
    returns=[math.log(b/a) for a,b in zip(closes[-25:-1],closes[-24:])]
    volatility=statistics.pstdev(returns)*math.sqrt(6)
    if volatility>0.12:return "extreme"
    if fast>slow*1.005:return "bull"
    if fast<slow*0.995:return "bear"
    return "sideways"

def candidates(bars,config=Config()):
    """Signals generated after close; caller must execute at next bar open."""
    if len(bars)<48*36:return []
    regime=classify(bars)
    h1=aggregate(bars,12)
    if len(h1)<50:return []
    c=[b["close"] for b in bars]
    h=[b["close"] for b in h1]
    price=c[-1]
    atr=statistics.fmean(max(b["high"]-b["low"],abs(b["high"]-p["close"]),abs(b["low"]-p["close"])) for p,b in zip(bars[-145:-1],bars[-144:]))
    distance=max(0.012,min(0.05,2*atr/price))
    trend=statistics.fmean(h[-12:])>statistics.fmean(h[-48:])
    # Require a prior confirmed break followed by a close above the retested level.
    level=max(c[-62:-14])
    previous_break=max(c[-13:-1])>level
    retest=min(b["low"] for b in bars[-12:])<=level*(1+config.breakout_retest_tolerance)
    relative_volume=bars[-1]["volume"]/max(1e-12,statistics.fmean(b["volume"] for b in bars[-49:-1]))
    quote_volume=float(bars[-1].get("quote_volume",price*bars[-1]["volume"]))
    range_fraction=(bars[-1]["high"]-bars[-1]["low"])/price
    breakout=(previous_break and retest and price>level and
              (price/level-1)<=config.breakout_max_extension and
              relative_volume>=config.breakout_volume_ratio and
              quote_volume>=config.breakout_min_quote_volume and
              range_fraction<=config.breakout_max_range)
    mean=statistics.fmean(c[-48:])
    sd=statistics.pstdev(c[-48:])
    z=(price-mean)/sd if sd else 0
    proposals=[]
    if regime=="bull" and trend and c[-1]>c[-13]:
        proposals.append(("trend",2.4,0.46))
    if regime=="bull" and trend and breakout:
        proposals.append(("breakout",2.8,0.43))
    if regime=="sideways" and z< -1.8:
        proposals.append(("mean_reversion",1.7,0.48))
    output=[]
    calibrated=dict(config.learned_priors)
    for name,reward_risk,prior in proposals:
        if name not in config.enabled_strategies: continue
        prior=calibrated.get(name,prior)
        if config.learned_model:
            from learner_v4 import predict
            prior=predict(config.learned_model,dict(strategy=name,regime=regime,stop_distance=distance,reward_risk=reward_risk,estimated_net=0))
            if config.calibration_model:
                from v4_extension import calibrated_probability
                prior=calibrated_probability(prior,config.calibration_model)
        # V4 applies the held-out Platt calibration before the expected-value gate.
        costs=2*(config.fee+config.half_spread+config.slippage)
        expected=prior*(distance*reward_risk)-(1-prior)*distance-costs
        output.append(dict(strategy=name,regime=regime,stop_distance=distance,
                           reward_risk=reward_risk,estimated_net=expected,
                           eligible=expected>config.min_expected_net))
    return output

def allocate(equity,cash,existing_exposure,stop_distance,config=Config(),daily_loss=0,drawdown=0):
    if equity<=0 or cash<=0 or daily_loss>=config.max_daily_loss or drawdown>=config.max_drawdown:
        return 0.0
    max_by_risk=equity*config.risk_fraction/(stop_distance+2*(config.fee+config.half_spread+config.slippage))
    return max(0.0,min(cash,max_by_risk,equity*config.max_exposure-existing_exposure))

def decision(bars,equity,cash,existing_exposure=0,daily_loss=0,drawdown=0,config=Config()):
    choices=[x for x in candidates(bars,config) if x["eligible"]]
    if not choices:return None
    best=max(choices,key=lambda x:x["estimated_net"])
    amount=allocate(equity,cash,existing_exposure,best["stop_distance"],config,daily_loss,drawdown)
    if amount<5:return None
    return dict(best,allocation=amount,execution="next_5m_open",live_trading=False)
