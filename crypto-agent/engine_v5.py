"""V5 research-only accounting and event-driven paper execution foundation.
No exchange connectivity. Every fill updates cash and inventory atomically.
"""
from dataclasses import dataclass,field
from typing import Dict,List
from math import isfinite

@dataclass
class Order:
    id: str
    symbol: str
    side: str
    quantity: float
    remaining: float
    status: str="open"

@dataclass
class Fill:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float

@dataclass
class Portfolio:
    cash: float=200.0
    positions: Dict[str,float]=field(default_factory=dict)
    cost_basis: Dict[str,float]=field(default_factory=dict)
    realized_pnl: float=0.0
    fees_paid: float=0.0
    orders: Dict[str,Order]=field(default_factory=dict)
    fills: List[Fill]=field(default_factory=list)

    def place(self,order_id,symbol,side,quantity):
        if side not in ("buy","sell") or quantity<=0 or not isfinite(quantity):
            raise ValueError("Invalid order")
        if order_id in self.orders:raise ValueError("Duplicate order ID")
        if side=="sell" and self.available_quantity(symbol)<quantity-1e-10:
            raise ValueError("Insufficient inventory")
        order=Order(order_id,symbol,side,quantity,quantity)
        self.orders[order_id]=order
        return order

    def available_quantity(self,symbol):
        reserved=sum(o.remaining for o in self.orders.values()
                     if o.symbol==symbol and o.side=="sell" and o.status=="open")
        return self.positions.get(symbol,0.)-reserved

    def execute(self,order_id,quantity,price,fee_rate):
        order=self.orders[order_id]
        if order.status!="open" or quantity<=0 or quantity>order.remaining+1e-10:
            raise ValueError("Invalid fill quantity")
        if price<=0 or fee_rate<0 or not all(map(isfinite,(quantity,price,fee_rate))):
            raise ValueError("Invalid fill price or fee")
        gross=quantity*price
        fee=gross*fee_rate
        held=self.positions.get(order.symbol,0.)
        if order.side=="buy":
            if gross+fee>self.cash+1e-9:raise ValueError("Insufficient cash")
            self.cash-=gross+fee
            self.positions[order.symbol]=held+quantity
            self.cost_basis[order.symbol]=self.cost_basis.get(order.symbol,0.)+gross+fee
        else:
            if quantity>held+1e-9:raise ValueError("Insufficient holdings")
            basis=self.cost_basis.get(order.symbol,0.)*(quantity/held)
            self.cash+=gross-fee
            self.positions[order.symbol]=max(0.,held-quantity)
            self.cost_basis[order.symbol]=max(0.,self.cost_basis.get(order.symbol,0.)-basis)
            self.realized_pnl+=gross-fee-basis
        self.fees_paid+=fee
        order.remaining=max(0.,order.remaining-quantity)
        if order.remaining<=1e-10:order.status="filled"
        fill=Fill(order.id,order.symbol,order.side,quantity,price,fee)
        self.fills.append(fill)
        return fill

    def cancel(self,order_id):
        order=self.orders[order_id]
        if order.status!="open":raise ValueError("Order is not open")
        order.status="cancelled"
        return order.remaining

    def equity(self,prices):
        return self.cash+sum(qty*prices[symbol] for symbol,qty in self.positions.items()
                             if qty>0)

    def reconcile(self,prices):
        equity=self.equity(prices)
        if self.cash < -1e-8 or any(q < -1e-8 for q in self.positions.values()):
            raise AssertionError("Negative cash or inventory")
        if not isfinite(equity):raise AssertionError("Nonfinite equity")
        return {"cash":self.cash,"equity":equity,"realized_pnl":self.realized_pnl,
                "fees_paid":self.fees_paid,"open_orders":sum(o.status=="open" for o in self.orders.values())}
