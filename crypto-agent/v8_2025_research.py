"""V8 2025 research: preserve real 5m OHLCV provenance, aggregate to 1h.
Use 2025-only train/validation/untouched-test, never rank on test outcomes.
"""
import csv,json,datetime as dt
from pathlib import Path
from v8_strategy_research import evaluate
from v8_price_behaviour import characterize

def hourly_from_5m(folder="crypto-agent/data_5m"):
    result={}
    for path in sorted(Path(folder).glob("*.csv")):
        rows=list(csv.DictReader(path.open()))
        if not rows:raise ValueError(f"Empty data: {path}")
        aggregated={}
        for row in rows:
            timestamp=dt.datetime.fromisoformat(row["timestamp"])
            if timestamp.year!=2025:raise ValueError("Non-2025 candle")
            key=timestamp.replace(minute=0,second=0,microsecond=0).isoformat()
            price={k:float(row[k]) for k in ("open","high","low","close","volume","quote_volume")}
            if key not in aggregated:
                aggregated[key]=dict(price)
                aggregated[key]["count"]=0
            item=aggregated[key]
            item["high"]=max(item["high"],price["high"])
            item["low"]=min(item["low"],price["low"])
            item["close"]=price["close"]
            if item["count"]:
                item["volume"]+=price["volume"]
                item["quote_volume"]+=price["quote_volume"]
            item["count"]+=1
        if len(aggregated)!=8760 or any(v["count"]!=12 for v in aggregated.values()):
            raise ValueError(f"Hourly coverage incomplete for {path.stem}")
        result[path.stem]={t:{k:v for k,v in bar.items() if k!="count"}
                           for t,bar in aggregated.items()}
    if set(result)!={"BTCUSDT","ETHUSDT"}:
        raise ValueError("BTC and ETH 2025 required")
    return result

def main():
    data=hourly_from_5m()
    comparison=evaluate(data)
    behaviour=characterize(data)
    report={"year":2025,"source":"Binance real 5-minute spot candles",
            "evaluation_frequency":"1h aggregated from 5m (not tick/L2)",
            "hourly_bars_per_symbol":8760,"strategy_comparison":comparison,
            "price_behaviour":behaviour,"real_orders":False,
            "warning":"No exchange depth or real fill guarantees; parameter search risks overfitting"}
    path=Path("crypto-agent/v8-2025-research.json")
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps({"year":2025,"selected":comparison["selected"],
                      "tested":comparison["tested"],"symbols":list(data)},indent=2))
if __name__=="__main__":main()
