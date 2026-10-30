"""V8 isolated margin paper simulator.
Long-only isolated leverage, conservative intrabar liquidation before take profit.
Research model: simplified liquidation, NOT exchange-specific margin rules.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass
class MarginPosition:
    entry:float
    quantity:float
    collateral:float
    borrowed:float
    leverage:float
    liquidation_price:float

class MarginLedger:
    def __init__(self,cash=200.,fee=.001,maintenance=.005,funding_per_8h=.0001):
        self.cash=float(cash);self.fee=fee;self.maintenance=maintenance
        self.funding_per_8h=funding_per_8h;self.position=None
        self.realized=0.;self.fees=0.;self.funding=0.;self.liquidations=0
        self.journal=[]
    def open(self,price,collateral,leverage):
        if self.position is not None:raise ValueError("Position already open")
        if not (price>0 and collateral>0 and collateral<=self.cash and 1<=leverage<=2):
            raise ValueError("Invalid collateral or leverage")
        notional=collateral*leverage
        entry_fee=notional*self.fee
        if collateral+entry_fee>self.cash:raise ValueError("Insufficient cash for entry fee")
        qty=notional/price;borrowed=notional-collateral
        # Equity = qty*price - borrowed - exit fee; maintenance = notional*maintenance.
        liq=(borrowed/(qty*(1-self.fee-self.maintenance)))
        self.cash-=collateral+entry_fee
        self.fees+=entry_fee
        self.position=MarginPosition(price,qty,collateral,borrowed,leverage,liq)
        self.journal.append({"event":"open","price":price,"collateral":collateral,
                             "leverage":leverage,"entry_fee":entry_fee})
    def mark(self,high,low,close,hours=0):
        p=self.position
        if p is None:return None
        if min(high,low,close)<=0 or low>high:raise ValueError("Invalid candle")
        funding=p.quantity*close*self.funding_per_8h*hours/8
        self.funding+=funding
        # Adverse first: stop/liquidation before favorable targets.
        if low<=p.liquidation_price:
            self.close(p.liquidation_price,liquidated=True)
            return "liquidation"
        return "open"
    def close(self,price,liquidated=False):
        p=self.position
        if p is None:raise ValueError("No position")
        proceeds=p.quantity*price
        exit_fee=proceeds*self.fee
        equity=proceeds-p.borrowed-exit_fee
        # Funding is deducted from the remaining collateral.
        payout=max(0.,equity-self.funding)
        pnl=payout-p.collateral
        self.cash+=payout;self.fees+=exit_fee;self.realized+=pnl
        if liquidated:self.liquidations+=1
        self.journal.append({"event":"liquidation" if liquidated else "close",
                             "price":price,"pnl":pnl,"exit_fee":exit_fee,
                             "funding":self.funding,"payout":payout})
        self.position=None;self.funding=0.
        return pnl
    def equity(self,price=None):
        if self.position is None:return self.cash
        if price is None:raise ValueError("Mark price required")
        p=self.position
        return self.cash+max(0,p.quantity*price-p.borrowed-p.quantity*price*self.fee-self.funding)
