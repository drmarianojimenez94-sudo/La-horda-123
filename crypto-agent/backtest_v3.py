"""Run V3 5-minute walk-forward research with transaction-level audit."""
import csv,json,math
from pathlib import Path
from strategy_v3 import Config,decision,classify
from backtest_v2 import load_data

def run(data,start,end,config=Config()):
    times=sorted(set().union(*(set(v) for v in data.values())))
    cash=200.;positions={};pending={};history={s:[] for s in data}
    ledger=[];curve=[];peak=200.;max_dd=0.;day=None;day_equity=200.;halt=False
    for t in times:
        if t < start or t >= end:
            if t >= end: break
            for sym, bar in ((sym, series[t]) for sym, series in data.items() if t in series):
                history[sym].append(bar)
                if len(history[sym]) > 2500: history[sym].pop(0)
            continue
        bars={s:v[t] for s,v in data.items() if t in v}
        active=start<=t<end
        if t[:10]!=day:
            day=t[:10];day_equity=cash+sum(p["qty"]*bars[s]["open"] for s,p in positions.items() if s in bars);halt=False
        if halt:
            pending.clear()
        for s,order in list(pending.items()):
            if active and not halt and s in bars and s not in positions and len(positions)<config.max_positions:
                px=bars[s]["open"]*(1+config.half_spread+config.slippage)
                qty=order["allocation"]/(px*(1+config.fee))
                if qty>0 and order["allocation"]<=cash:
                    cash-=order["allocation"]
                    positions[s]=dict(order,qty=qty,entry=px,entry_time=t,entry_cost=order["allocation"],
                                      stop=px*(1-order["stop_distance"]),
                                      target=px*(1+order["stop_distance"]*order["reward_risk"]),age=0)
            pending.pop(s,None)
        for s,p in list(positions.items()):
            if s not in bars:continue
            b=bars[s];p["age"]+=1
            reason=None;px=None
            if b["open"]<=p["stop"]:reason,px="gap_stop",b["open"]
            elif b["open"]>=p["target"]:reason,px="gap_target",b["open"]
            elif b["low"]<=p["stop"]:reason,px="stop",p["stop"]
            elif b["high"]>=p["target"]:reason,px="target",p["target"]
            elif p["age"]>=864:reason,px="timeout",b["close"]
            elif t>=end and active:reason,px="window_end",b["close"]
            if reason:
                exit_price=px*(1-config.half_spread-config.slippage)
                proceeds=p["qty"]*exit_price*(1-config.fee);cash+=proceeds
                ledger.append(dict(symbol=s,strategy=p["strategy"],regime=p["regime"],entry_time=p["entry_time"],exit_time=t,
                                   entry=p["entry"],exit=exit_price,quantity=p["qty"],cost=p["entry_cost"],
                                   proceeds=proceeds,pnl=proceeds-p["entry_cost"],reason=reason,stop_distance=p["stop_distance"],reward_risk=p["reward_risk"],estimated_net=p["estimated_net"]))
                del positions[s]
        equity=cash+sum(p["qty"]*bars[s]["close"] for s,p in positions.items() if s in bars)
        peak=max(peak,equity)
        drawdown=1-equity/peak
        if active:max_dd=max(max_dd,drawdown)
        daily_loss=max(0,1-equity/day_equity) if day_equity else 0
        if daily_loss>=config.max_daily_loss or drawdown>=config.max_drawdown:
            halt=True
            pending.clear()
            for sym,p in list(positions.items()):
                if sym not in bars: continue
                px=bars[sym]["close"]*(1-config.half_spread-config.slippage)
                proceeds=p["qty"]*px*(1-config.fee)
                cash+=proceeds
                ledger.append(dict(symbol=sym,strategy=p["strategy"],regime=p["regime"],entry_time=p["entry_time"],exit_time=t,entry=p["entry"],exit=px,quantity=p["qty"],cost=p["entry_cost"],proceeds=proceeds,pnl=proceeds-p["entry_cost"],reason="risk_liquidation",stop_distance=p["stop_distance"],reward_risk=p["reward_risk"],estimated_net=p["estimated_net"]))
                del positions[sym]
            equity=cash+sum(p["qty"]*bars[sym]["close"] for sym,p in positions.items() if sym in bars)
        if active:curve.append(dict(timestamp=t,equity=equity))
        for s,b in bars.items():
            history[s].append(b)
            if len(history[s])>2500:history[s].pop(0)
        if active and not halt:
            for s in bars:
                if s in positions or s in pending or len(positions)+len(pending)>=config.max_positions:continue
                used=sum(p["entry_cost"] for p in positions.values())+sum(p["allocation"] for p in pending.values())
                proposal=decision(history[s],equity,cash-sum(p["allocation"] for p in pending.values()),used,daily_loss,drawdown,config)
                if proposal:pending[s]=proposal
    # Liquidate at the final available close with explicit transaction costs.
    for sym,p in list(positions.items()):
        last=next((data[sym][ts] for ts in reversed(times) if start<=ts<end and ts in data[sym]),None)
        if last is None: continue
        px=last["close"]*(1-config.half_spread-config.slippage)
        proceeds=p["qty"]*px*(1-config.fee)
        cash+=proceeds
        ledger.append(dict(symbol=sym,strategy=p["strategy"],regime=p["regime"],entry_time=p["entry_time"],exit_time=end,entry=p["entry"],exit=px,quantity=p["qty"],cost=p["entry_cost"],proceeds=proceeds,pnl=proceeds-p["entry_cost"],reason="window_end",stop_distance=p["stop_distance"],reward_risk=p["reward_risk"],estimated_net=p["estimated_net"]))
        del positions[sym]
    # Remaining positions are valued conservatively if a symbol has no final bar.
    final=cash
    for s,p in positions.items():
        last=next((data[s][t] for t in reversed(times) if t<end and t in data[s]),None)
        if last:final+=p["qty"]*last["close"]*(1-config.half_spread-config.slippage)*(1-config.fee)
    return dict(final=final,return_pct=100*(final/200-1),max_drawdown_pct=100*max_dd,
                trades=len(ledger),ledger=ledger,equity_curve=curve)

def main():
    data=load_data("crypto-agent/data_5m")
    times=sorted(set().union(*(set(v) for v in data.values())))
    if len(times)<288*75:raise ValueError("Need >=75 days of 5-minute candles")
    step=288*15;first=max(288*45,len(times)-3*step)
    windows=[]
    for i in range(first,len(times)-step,step):
        windows.append(dict(start=times[i],end=times[i+step],result=run(data,times[i],times[i+step])))
    if not windows:raise ValueError("No complete validation windows")
    folder=Path("crypto-agent")
    with (folder/"trades_v3.csv").open("w",newline="") as f:
        fields=["window","symbol","strategy","regime","entry_time","exit_time","entry","exit","quantity","cost","proceeds","pnl","reason"]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for i,w in enumerate(windows):
            for row in w["result"]["ledger"]:writer.writerow(dict(window=i+1,**row))
    report={"model":"V3 exploratory, fixed uncalibrated signal priors","timeframe":"5m entry, 1h confirmation, 4h regime",
            "windows":[dict(start=w["start"],end=w["end"],final=w["result"]["final"],return_pct=w["result"]["return_pct"],max_drawdown_pct=w["result"]["max_drawdown_pct"],trades=w["result"]["trades"]) for w in windows],
            "aggregate_oos_return_pct":100*(math.prod(w["result"]["final"]/200 for w in windows)-1),
            "limitations":"No L2 order book, partial fills, short selling, funding, leverage or trained ML probabilities."}
    (folder/"audit_v3.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
