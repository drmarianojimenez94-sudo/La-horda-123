"""Unified V5 labels: every historical opportunity uses the same executable policy.
Causal signal at bar i close, entry at i+1 open, exit at horizon close.
Labels are net returns including two-sided fees, spread and slippage.
"""
from specialists_v5 import specialists

def label_opportunities(data,step=12,horizon=36,fee=.001,half_spread=.0003,slippage=.0005):
    rows=[]
    for symbol,series in data.items():
        times=sorted(series)
        for i in range(120,len(times)-horizon,step):
            history=[series[t] for t in times[max(0,i-2500):i+1]]
            for signal in specialists(history):
                entry=series[times[i+1]]["open"]*(1+half_spread+slippage)
                exit_price=series[times[i+horizon]]["close"]*(1-half_spread-slippage)
                gross=(exit_price*(1-fee))/(entry*(1+fee))-1
                rows.append({**signal,"symbol":symbol,"signal_time":times[i],
                    "entry_time":times[i+1],"label_end":times[i+horizon],
                    "net_return":gross,"pnl":gross,"label":int(gross>0),
                    "label_policy":"next_open_to_horizon_close_net_of_costs"})
    return rows

def purged_split(rows,train_end,cal_end,test_end):
    train=[x for x in rows if x["label_end"]<train_end]
    cal=[x for x in rows if x["signal_time"]>=train_end and x["label_end"]<cal_end]
    test=[x for x in rows if x["signal_time"]>=cal_end and x["label_end"]<test_end]
    return train,cal,test
