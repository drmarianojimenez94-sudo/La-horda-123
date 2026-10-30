"""V4 research gates: rejected opportunities, independent calibration and stress fills.
No live execution. OHLCV liquidity is a proxy, never historical L2 depth.
"""
from dataclasses import dataclass
from math import exp, log
from statistics import mean

@dataclass(frozen=True)
class FillScenario:
    name: str
    fee: float
    half_spread: float
    slippage: float
    participation: float
    volatility_multiplier: float = 0.0

SCENARIOS = (
    FillScenario('normal', .001, .0003, .0005, .02),
    FillScenario('adverse', .0015, .0008, .0015, .01, .5),
    FillScenario('extreme', .002, .002, .004, .005, 1.0),
)

def liquidity_features(bars):
    if len(bars)<24:return None
    window=bars[-24:]
    quote=[float(x.get('quote_volume',x['close']*x['volume'])) for x in window]
    if any(v<0 for v in quote):raise ValueError('Negative volume')
    avg=mean(quote)
    return {'quote_volume':quote[-1],'quote_volume_ratio':quote[-1]/avg if avg else 0.,
            'range_fraction':(window[-1]['high']-window[-1]['low'])/window[-1]['close'],
            'trade_count':int(window[-1].get('trade_count',0)),'depth_available':False}

def simulate_partial_fill(order_notional,bar,scenario=SCENARIOS[0],side='buy'):
    if order_notional<0:raise ValueError('negative notional')
    volume=float(bar.get('quote_volume',bar['volume']*bar['close']))
    if volume<0:raise ValueError('negative liquidity')
    filled=min(order_notional,volume*scenario.participation)
    range_frac=max(0.,(bar['high']-bar['low'])/bar['close'])
    friction=scenario.half_spread+scenario.slippage+scenario.volatility_multiplier*range_frac
    px=bar['open']*(1+friction if side=='buy' else 1-friction)
    return {'filled_notional':filled,'unfilled_notional':max(0.,order_notional-filled),
            'price':px,'fee':filled*scenario.fee,
            'fill_ratio':filled/order_notional if order_notional else 0.,
            'scenario':scenario.name,'model':'OHLCV participation proxy'}

def candidate_opportunities(data,make_candidates,lookback=2500,step=12,horizon=36):
    """All candidate signals, including rejected ones; label after horizon."""
    out=[]
    for symbol,rows in data.items():
        times=sorted(rows)
        for idx in range(1728,len(times)-horizon,step):
            past=[rows[t] for t in times[max(0,idx-lookback+1):idx+1]]
            for candidate in make_candidates(past):
                future=rows[times[idx+horizon]]['close']
                entry=rows[times[idx+1]]['open']
                outcome=future/entry-1-.0036
                out.append({'symbol':symbol,'signal_time':times[idx],
                            'entry_time':times[idx+1],'label_end':times[idx+horizon],
                            'strategy':candidate['strategy'],'regime':candidate['regime'],
                            'stop_distance':candidate['stop_distance'],
                            'reward_risk':candidate['reward_risk'],
                            'estimated_net':candidate['estimated_net'],
                            'rejected':not candidate['eligible'],
                            'pnl':outcome,'label':int(outcome>0),
                            'label_kind':'fixed_horizon_net_return_proxy'})
    return out

def partition(opportunities,train_end,calibration_end,test_end):
    train=[x for x in opportunities if x['label_end']<train_end]
    calibration=[x for x in opportunities if x['signal_time']>=train_end and x['label_end']<calibration_end]
    test=[x for x in opportunities if x['signal_time']>=calibration_end and x['label_end']<test_end]
    return train,calibration,test

def fit_platt(scores,labels,epochs=400,rate=.08):
    if len(scores)!=len(labels) or len(scores)<30:return None
    a,b=1.,0.
    for _ in range(epochs):
        ga=gb=0.
        for p,y in zip(scores,labels):
            z=log(max(1e-6,min(1-1e-6,p))/(1-max(1e-6,min(1-1e-6,p))))
            v=1/(1+exp(-max(-30,min(30,a*z+b))))
            ga+=(v-y)*z;gb+=v-y
        a-=rate*ga/len(scores);b-=rate*gb/len(scores)
    return a,b

def calibrated_probability(probability,model):
    if model is None:return None
    p=max(1e-6,min(1-1e-6,probability))
    z=log(p/(1-p))
    return 1/(1+exp(-max(-30,min(30,model[0]*z+model[1]))))

def brier(scores,labels):
    return sum((p-y)**2 for p,y in zip(scores,labels))/len(scores) if scores else None

def stress_report(trades):
    result={}
    for scenario in SCENARIOS:
        extra=2*((scenario.fee-.001)+(scenario.half_spread-.0003)+(scenario.slippage-.0005))
        pnl=sum(float(t['pnl'])-float(t.get('cost',0))*extra for t in trades)
        result[scenario.name]={'adjusted_net_pnl':round(pnl,6),'trades':len(trades),'approximate':True}
    return result
