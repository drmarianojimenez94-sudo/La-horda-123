"""V5 specialist research signals; causal OHLCV only, no historical L2 claims."""
from statistics import mean,pstdev

def specialists(bars):
    if len(bars)<120:return []
    close=[float(x["close"]) for x in bars]
    price=close[-1]
    if price<=0:return []
    fast=mean(close[-24:]);slow=mean(close[-96:])
    vol=pstdev([(close[i]/close[i-1]-1) for i in range(-48,0)])
    quote=float(bars[-1].get("quote_volume",price*bars[-1]["volume"]))
    volume_ratio=bars[-1]["volume"]/max(1e-9,mean(b["volume"] for b in bars[-49:-1]))
    if quote<100000 or vol>.035:return []
    momentum_1h=price/close[-13]-1
    momentum_4h=price/close[-49]-1
    volatility_ratio=vol/max(1e-9,pstdev([(close[i]/close[i-1]-1) for i in range(-96,-48)))
    taker=float(bars[-1].get("taker_buy_base",0))
    buy_imbalance=taker/max(1e-9,float(bars[-1]["volume"])) if taker else .5
    context={"momentum_1h":momentum_1h,"momentum_4h":momentum_4h,
             "volatility_ratio":min(10.,volatility_ratio),"relative_volume":volume_ratio,
             "buy_imbalance":min(1.,buy_imbalance),"trend_strength":fast/slow-1}
    signals=[]
    if fast>slow*1.003 and price>close[-13]:
        signals.append({"strategy":"trend","regime":"bull","score":(fast/slow-1),"stop_distance":.018,"reward_risk":2.2})
    level=max(close[-62:-14])
    if max(close[-13:-1])>level and min(x["low"] for x in bars[-12:])<=level*1.004 and price>level and volume_ratio>=1.3 and price/level<1.008:
        signals.append({"strategy":"breakout","regime":"bull","score":volume_ratio-1,"stop_distance":.018,"reward_risk":2.5})
    average=mean(close[-48:]);sd=pstdev(close[-48:])
    if sd and (price-average)/sd< -2 and fast>=slow*.995:
        signals.append({"strategy":"mean_reversion","regime":"sideways","score":(average-price)/sd,"stop_distance":.015,"reward_risk":1.7})
    # Taker-buy fraction is candle flow, NOT L2 order book imbalance.
    return [{**signal,**context} for signal in signals]
