"""Compatibility adapter to canonical V8 execution and accounting."""
from v8_unified_ledger import UnifiedSpotLedger

class SharedPortfolio(UnifiedSpotLedger):
    def __init__(self,cash=200.,fee=.001,impact=.0008):
        super().__init__(cash,fee,impact,max_exposure=.30)
        self.ledger=[]
    def buy(self,symbol,price,prices,max_notional=None):
        return super().buy(symbol,price,prices,notional_cap=20. if max_notional is None else max_notional)
    def sell(self,symbol,price):
        pnl=super().sell(symbol,price)
        self.ledger.append({"symbol":symbol,"pnl":pnl})
        return pnl
