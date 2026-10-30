"""V8 common spot paper execution/accounting for both strategy laboratories."""
class UnifiedSpotLedger:
    def __init__(self,cash=200.,fee=.001,impact=.0008,max_exposure=.30):
        self.initial=float(cash);self.cash=float(cash);self.fee=fee
        self.impact=impact;self.max_exposure=max_exposure
        self.positions={};self.journal=[];self.fees=0.
    def equity(self,prices):
        return self.cash+sum(p["qty"]*prices[s] for s,p in self.positions.items())
    def exposure(self,prices):
        return sum(p["qty"]*prices[s] for s,p in self.positions.items())
    def buy(self,symbol,raw_price,prices,notional_cap=20.,time=None):
        if symbol in self.positions or raw_price<=0:return False
        equity=self.equity(prices)
        available=max(0.,equity*self.max_exposure-self.exposure(prices))
        budget=min(self.cash,notional_cap,available)
        if budget<5:return False
        fill_price=raw_price*(1+self.impact)
        qty=budget/(fill_price*(1+self.fee))
        fee=qty*fill_price*self.fee
        cost=qty*fill_price+fee
        self.cash-=cost;self.fees+=fee
        self.positions[symbol]={"qty":qty,"cost":cost,"entry":fill_price}
        self.journal.append({"kind":"buy","symbol":symbol,"time":time,
                             "price":fill_price,"qty":qty,"fee":fee,"cash":self.cash})
        return True
    def sell(self,symbol,raw_price,time=None,reason="exit"):
        if symbol not in self.positions:raise ValueError("No open position")
        p=self.positions.pop(symbol)
        fill_price=raw_price*(1-self.impact)
        gross=p["qty"]*fill_price
        fee=gross*self.fee;proceeds=gross-fee
        self.cash+=proceeds;self.fees+=fee
        pnl=proceeds-p["cost"]
        self.journal.append({"kind":"sell","symbol":symbol,"time":time,
                             "price":fill_price,"qty":p["qty"],"fee":fee,
                             "pnl":pnl,"reason":reason,"cash":self.cash})
        return pnl
    def reconcile(self,prices):
        equity=self.equity(prices)
        buys=sum(x["qty"]*x["price"]+x["fee"] for x in self.journal if x["kind"]=="buy")
        sells=sum(x["qty"]*x["price"]-x["fee"] for x in self.journal if x["kind"]=="sell")
        assert abs(self.cash-(self.initial-buys+sells))<1e-6
        assert equity>=-1e-6
        return {"cash":self.cash,"equity":equity,"fees":self.fees,
                "realized_pnl":sum(x.get("pnl",0) for x in self.journal),
                "fills":len(self.journal),"reconciled":True}
