"""Event-driven paper-only microstructure engine.
No credentials, no live orders. Decisions use executable bid/ask and fees.
"""
from dataclasses import dataclass
from math import isfinite
from engine_v5 import Portfolio

@dataclass(frozen=True)
class BookEvent:
    timestamp_ms:int
    symbol:str
    bid:float
    ask:float
    bid_qty:float
    ask_qty:float

def features(event):
    if min(event.bid,event.ask)<=0 or min(event.bid_qty,event.ask_qty)<0:
        raise ValueError("Invalid order book")
    if event.ask<event.bid:raise ValueError("Crossed book")
    midpoint=(event.bid+event.ask)/2
    total=event.bid_qty+event.ask_qty
    return {"spread":(event.ask-event.bid)/midpoint,
            "imbalance":(event.bid_qty-event.ask_qty)/total if total else 0.,
            "mid":midpoint}

class EventPaperAgent:
    def __init__(self,initial=200.,fee=.001,min_net_edge=.002,max_notional=20.,
                 max_spread=.001,stale_after_ms=5000):
        self.portfolio=Portfolio(initial)
        self.fee=fee
        self.min_net_edge=min_net_edge
        self.max_notional=max_notional
        self.max_spread=max_spread
        self.stale_after_ms=stale_after_ms
        self.last={}
        self.events=0
        self.rejections={}
        self.journal=[]
    def reject(self,reason):
        self.rejections[reason]=self.rejections.get(reason,0)+1
        return None
    def on_book(self,event,forecast_net,now_ms=None):
        f=features(event)
        now_ms=event.timestamp_ms if now_ms is None else now_ms
        if now_ms-event.timestamp_ms>self.stale_after_ms or event.timestamp_ms>now_ms:
            return self.reject("stale_book")
        prior=self.last.get(event.symbol)
        if prior is not None and event.timestamp_ms<=prior:
            return self.reject("out_of_order")
        self.last[event.symbol]=event.timestamp_ms
        self.events+=1
        self.journal.append({"timestamp_ms":event.timestamp_ms,"symbol":event.symbol,
                             "spread":f["spread"],"imbalance":f["imbalance"],
                             "forecast_net":forecast_net})
        if not isfinite(forecast_net):return self.reject("invalid_prediction")
        if f["spread"]>self.max_spread:return self.reject("spread")
        # Forecast is pre-cost expected price return. Require executable edge.
        net=forecast_net-f["spread"]-2*self.fee
        if net<self.min_net_edge:return self.reject("insufficient_edge")
        if self.portfolio.positions.get(event.symbol,0)>0:return self.reject("already_held")
        qty=min(self.max_notional,self.portfolio.cash*.1)/(event.ask*(1+self.fee))
        if qty<=0:return self.reject("no_cash")
        oid=f"paper:{event.symbol}:{event.timestamp_ms}"
        self.portfolio.place(oid,event.symbol,"buy",qty)
        fill=self.portfolio.execute(oid,qty,event.ask,self.fee)
        return fill
    def snapshot(self):
        return {"events":self.events,"rejections":self.rejections,
                "last_timestamps":self.last,"fills":len(self.portfolio.fills),
                "cash":self.portfolio.cash}
