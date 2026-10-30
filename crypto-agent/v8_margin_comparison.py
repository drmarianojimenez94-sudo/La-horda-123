"""Compare selected candidate in spot and isolated-margin paper accounts.
Liquidation is checked on each candle low, before target/stop exits.
"""
from v8_margin_ledger import MarginLedger
from v8_strategy_research import signal

def margin_simulate(bars,c,start,end,leverage=1.):
    account=MarginLedger()
    deadline=None;stop=None;target=None;peak=200.;dd=0.
    for i in range(start,min(end,len(bars))):
        b=bars[i]
        if account.position:
            state=account.mark(b["high"],b["low"],b["close"],hours=5/60)
            if state=="liquidation":
                deadline=None
            elif b["low"]<=stop:
                account.close(min(b["open"],stop));deadline=None
            elif b["high"]>=target:
                account.close(max(b["open"],target));deadline=None
            elif i>=deadline or i==end-1:
                account.close(b["close"]);deadline=None
        equity=account.equity(b["close"])
        peak=max(peak,equity);dd=max(dd,1-equity/peak)
        if (account.position is None and i>start and i<end-1
                and signal(bars,i-1,c)):
            collateral=min(20.,account.cash*.1/(1+leverage*.001))
            if collateral>=5:
                entry=b["open"]*1.0008
                account.open(entry,collateral,leverage)
                stop=entry*(1-c["stop"]);target=entry*(1+c["target"])
                deadline=i+c["max_bars"]
                # Liquidation or stop can happen in the entry candle.
                state=account.mark(b["high"],b["low"],b["close"],hours=0)
                if state=="liquidation":deadline=None
                elif b["low"]<=stop:
                    account.close(min(b["open"],stop));deadline=None
                elif b["high"]>=target:
                    account.close(max(b["open"],target));deadline=None
    if account.position:account.close(bars[min(end,len(bars))-1]["close"])
    return {"leverage":leverage,"return_pct":100*(account.cash/200-1),
            "liquidations":account.liquidations,"fees":account.fees,
            "max_drawdown_pct":100*dd,"realized_pnl":account.realized,
            "paper_only":True}

def compare_selected(data,candidate):
    if candidate is None:return {"status":"cash_selected","scenarios":[]}
    results={}
    for symbol,series in data.items():
        bars=[series[t] for t in sorted(series)]
        start=int(len(bars)*.8)
        results[symbol]=[margin_simulate(bars,candidate,start,len(bars),level)
                         for level in (1.,1.25,1.5,2.)]
    return {"status":"paper_margin_comparison","scenarios":results,
            "note":"Simplified isolated margin and funding, not exchange liquidation pricing."}
