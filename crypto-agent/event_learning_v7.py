"""V7 causal learning samples from persisted best-bid/ask events.
Every observed quote is eligible for a shadow label, even if no order was placed.
This creates training DATA, not a trained trading model or a profitable strategy.
"""
from statistics import mean
from math import isfinite

def build_shadow_labels(events,horizon_ms=60000,fee=.001,min_gap_ms=1000):
    """Events sorted by exchange-observation timestamp. Buy at ask, sell at later bid.
    The future label is only emitted after horizon has elapsed; never used for live decisions.
    """
    by_symbol={}
    for event in events:
        if event.get("kind")!="book_ticker":continue
        p=event["payload"]
        if not all(k in p for k in ("bid","ask","bid_qty","ask_qty")):continue
        if p["bid"]<=0 or p["ask"]<p["bid"]:continue
        by_symbol.setdefault(event["symbol"],[]).append(event)
    samples=[]
    for symbol,rows in by_symbol.items():
        rows.sort(key=lambda e:e["timestamp_ms"])
        j=0;last_sample=-10**30
        for i,event in enumerate(rows):
            t=event["timestamp_ms"]
            if t-last_sample<min_gap_ms:continue
            j=max(j,i+1)
            while j<len(rows) and rows[j]["timestamp_ms"]<t+horizon_ms:j+=1
            if j==len(rows):break
            first=event["payload"];future=rows[j]["payload"]
            ask=float(first["ask"]);bid=float(future["bid"])
            net=bid*(1-fee)/(ask*(1+fee))-1
            total=float(first["bid_qty"])+float(first["ask_qty"])
            samples.append({"symbol":symbol,"signal_time_ms":t,
                "label_end_ms":rows[j]["timestamp_ms"],
                "spread":(ask-float(first["bid"]))/((ask+float(first["bid"]))/2),
                "imbalance":(float(first["bid_qty"])-float(first["ask_qty"]))/total if total else 0.,
                "net_return":net,"label":int(net>0),
                "label_policy":"buy_ask_sell_future_bid_fee_adjusted"})
            last_sample=t
    return samples

def purged_time_split(samples,train_end_ms,cal_end_ms,test_end_ms):
    train=[s for s in samples if s["label_end_ms"]<train_end_ms]
    cal=[s for s in samples if s["signal_time_ms"]>=train_end_ms and s["label_end_ms"]<cal_end_ms]
    test=[s for s in samples if s["signal_time_ms"]>=cal_end_ms and s["label_end_ms"]<test_end_ms]
    return train,cal,test

def drift_summary(samples):
    if not samples:return {"samples":0,"ready":False}
    return {"samples":len(samples),"mean_net_return":mean(s["net_return"] for s in samples),
            "win_rate":mean(s["label"] for s in samples),
            "mean_spread":mean(s["spread"] for s in samples),
            "ready":len(samples)>=100}
