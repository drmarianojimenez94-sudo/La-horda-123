"""Deterministic offline paper execution: no network, no real orders."""
from dataclasses import dataclass
from engine_v5 import Portfolio

@dataclass(frozen=True)
class MarketConditions:
    participation: float=.01
    fee: float=.001
    spread: float=.0006
    slippage: float=.0005
    max_range: float=.08

def paper_fill(portfolio,order_id,bar,conditions=MarketConditions()):
    order=portfolio.orders[order_id]
    if order.status!="open":return None
    if not 0<conditions.participation<=1:raise ValueError("Invalid participation")
    if not 0<=conditions.spread<1 or conditions.slippage<0:raise ValueError("Invalid friction")
    if not 0<=conditions.fee<1:raise ValueError("Invalid fee")
    if bar["open"]<=0 or bar["close"]<=0 or bar["volume"]<0:
        raise ValueError("Invalid candle")
    if (bar["high"]-bar["low"])/bar["close"]>conditions.max_range:return None
    px=bar["open"]*(1+(conditions.spread/2+conditions.slippage)*(1 if order.side=="buy" else -1))
    quote_volume=float(bar.get("quote_volume",bar["volume"]*bar["close"]))
    cap=quote_volume*conditions.participation/px
    qty=min(order.remaining,max(0.,cap))
    if order.side=="buy":
        qty=min(qty,portfolio.cash/(px*(1+conditions.fee)))
    else:
        qty=min(qty,portfolio.positions.get(order.symbol,0.))
    if qty<=1e-12:return None
    return portfolio.execute(order_id,qty,px,conditions.fee)
