"""Price behaviour research on actual 5m OHLCV; no fabricated order book."""
import json,math
from pathlib import Path
from statistics import mean,pstdev
from backtest_v2 import load_data

def characterize(data):
    output={}
    for symbol,series in data.items():
        keys=sorted(series);bars=[series[k] for k in keys]
        if len(bars)<300:continue
        returns=[bars[i]["close"]/bars[i-1]["close"]-1 for i in range(1,len(bars))]
        ranges=[(b["high"]-b["low"])/max(b["open"],1e-9) for b in bars]
        volumes=[b["quote_volume"] for b in bars]
        def summary(segment):
            r=segment
            return {"mean_return_pct":100*mean(r),"volatility_pct":100*pstdev(r),
                    "positive_fraction":sum(x>0 for x in r)/len(r),
                    "worst_candle_pct":100*min(r),"best_candle_pct":100*max(r)}
        block=288
        daily=[math.prod(1+x for x in returns[i:i+block])-1
               for i in range(0,len(returns)-block+1,block)]
        peak=0.;max_dd=0.
        for bar in bars:
            peak=max(peak,bar["close"])
            max_dd=max(max_dd,1-bar["close"]/peak)
        output[symbol]={"candles":len(bars),"first":keys[0],"last":keys[-1],
            "total_return_pct":100*(bars[-1]["close"]/bars[0]["open"]-1),
            "five_minute":summary(returns),"daily":summary(daily) if daily else None,
            "mean_range_pct":100*mean(ranges),
            "mean_quote_volume":mean(volumes),
            "volume_spike_fraction":sum(v>2*mean(volumes) for v in volumes)/len(volumes),
            "maximum_drawdown_pct":100*max_dd}
    return {"data_type":"real_historical_5m_OHLCV","symbols":output,
            "warning":"OHLCV contains no historical bid/ask or order-book depth."}

if __name__=="__main__":
    result=characterize(load_data())
    Path("crypto-agent/v8-price-behaviour.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({k:{"candles":v["candles"],"total_return_pct":v["total_return_pct"]}
                      for k,v in result["symbols"].items()},indent=2))
