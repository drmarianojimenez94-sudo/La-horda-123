"""Honest OHLCV-only six-month benchmarks. Never call candles L2/order-book events."""
import json
from pathlib import Path
from backtest_v2 import load_data

def report(data):
    assets={}
    for symbol,series in data.items():
        keys=sorted(series)
        if len(keys)<2:continue
        first=series[keys[0]]["open"]
        last=series[keys[-1]]["close"]
        assets[symbol]={"candles":len(keys),"buy_hold_return_pct":100*(last/first-1)}
    equal=sum(x["buy_hold_return_pct"] for x in assets.values())/len(assets) if assets else None
    return {"data_type":"five_minute_OHLCV_not_order_book_events",
            "cash_return_pct":0.0,"assets":assets,
            "equal_weight_buy_hold_return_pct":equal,
            "note":"Buy/hold benchmark excludes execution costs; trading model accounts for modeled costs."}

if __name__=="__main__":
    result=report(load_data())
    Path("crypto-agent/benchmark_180d.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
