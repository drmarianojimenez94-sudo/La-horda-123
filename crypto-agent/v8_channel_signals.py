"""Channel breakout confirmation research on completed candles."""
from statistics import mean

def atr(bars,i,n=14):
    if i<n:return 0.
    return mean(max(bars[k]["high"]-bars[k]["low"],
                    abs(bars[k]["high"]-bars[k-1]["close"]),
                    abs(bars[k]["low"]-bars[k-1]["close"]))
                for k in range(i-n+1,i+1))

def confirmed(bars,i,lookback=48,volume_multiple=1.5):
    if i<max(100,lookback+20):return False
    past=bars[i-lookback:i]
    resistance=max(x["high"] for x in past)
    av=mean(x["volume"] for x in past)
    current_atr=atr(bars,i)
    old_atr=mean(atr(bars,k) for k in range(i-20,i))
    return (bars[i]["close"]>resistance
            and bars[i]["volume"]>=volume_multiple*av
            and old_atr>0 and .8<=current_atr/old_atr<=2.5
            and bars[i]["close"]-resistance<=1.5*current_atr)

def updated_stop(old_stop,close,atr_value,mode="trailing"):
    factor=2 if mode=="atr" else 3
    return max(old_stop,close-factor*atr_value)
