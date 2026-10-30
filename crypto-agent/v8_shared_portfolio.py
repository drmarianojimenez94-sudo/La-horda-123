"""Shared spot cash ledger; paper research only."""
class SharedPortfolio:
    def __init__(self,cash=200.,fee=.001,impact=.0008):
        self.cash=cash;self.fee=fee;self.impact=impact
        self.positions={};self.ledger=[]
    def equity(self,prices):
        return self.cash+sum(p["qty"]*prices[s] for s,p in self.positions.items())
    def buy(self,symbol,price,prices):
        if symbol in self.positions:return False
        equity=self.equity(prices)
        invested=equity-self.cash
        budget=min(20.,self.cash,max(0.,equity*.3-invested))
        if budget<5:return False
        px=price*(1+self.impact)
        qty=budget/(px*(1+self.fee))
        self.cash-=budget
        self.positions[symbol]={"qty":qty,"cost":budget}
        return True
    def sell(self,symbol,price):
        p=self.positions.pop(symbol)
        proceeds=p["qty"]*price*(1-self.impact)*(1-self.fee)
        self.cash+=proceeds
        self.ledger.append({"symbol":symbol,"pnl":proceeds-p["cost"]})
