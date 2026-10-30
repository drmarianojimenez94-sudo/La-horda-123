"""Shared spot cash ledger; paper research only."""
class SharedPortfolio:
    def __init__(self,cash=200.,fee=.001,impact=.0008):
        self.cash=cash;self.fee=fee;self.impact=impact
        self.positions={};self.ledger=[];self.fees=0.
    def equity(self,prices):
        return self.cash+sum(p["qty"]*prices[s] for s,p in self.positions.items())
    def buy(self,symbol,price,prices,max_notional=None):
        if symbol in self.positions:return False
        equity=self.equity(prices)
        invested=equity-self.cash
        budget=min(20.,self.cash,max(0.,equity*.3-invested))
        if max_notional is not None:budget=min(budget,max_notional)
        if budget<5:return False
        px=price*(1+self.impact)
        qty=budget/(px*(1+self.fee))
        self.cash-=budget
        self.fees+=qty*px*self.fee
        self.positions[symbol]={"qty":qty,"cost":budget}
        return True
    def sell(self,symbol,price):
        p=self.positions.pop(symbol)
        proceeds=p["qty"]*price*(1-self.impact)*(1-self.fee)
        self.cash+=proceeds
        self.fees+=p["qty"]*price*(1-self.impact)*self.fee
        self.ledger.append({"symbol":symbol,"pnl":proceeds-p["cost"]})
