import csv, json, math, statistics, urllib.request, datetime, time
from pathlib import Path
PROFILES={'conservadora':(10,3,.01,-1.6,.006,.018),'agresiva':(30,5,.03,-1.05,.011,.035),'adaptativa':(20,4,.02,-1.3,.008,.024)}
FEE=.001; SPREAD=.0006; SLIP=.0005
MIN_NET_TARGET=.01
MIN_REWARD_RISK=2.0
MAX_RISK_PER_TRADE=.005
MAX_DAILY_LOSS=.02
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CryptoAgentPaper/1.0'}),timeout=20) as r:return json.load(r)
def download(days=90,top=20):
 import io, zipfile, urllib.error
 root=Path('crypto-agent/data');root.mkdir(parents=True,exist_ok=True)
 # Fixed, liquid spot pairs; avoids selecting today's winners using future information.
 names=['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','ADAUSDT','DOGEUSDT','TRXUSDT','LINKUSDT','AVAXUSDT']
 today=datetime.datetime.now(datetime.timezone.utc).date()
 finish=today-datetime.timedelta(days=1)
 begin=finish-datetime.timedelta(days=days-1)
 for symbol in names:
  rows=[]
  day=begin
  while day<=finish:
   d=day.isoformat()
   url=f'https://data.binance.vision/data/spot/daily/klines/{symbol}/1h/{symbol}-1h-{d}.zip'
   try:
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:
     payload=response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
     with z.open(z.namelist()[0]) as source:
      reader=csv.reader(io.TextIOWrapper(source,encoding='utf-8-sig'))
      for b in reader:
       if not b or not b[0].isdigit():continue
       ts=int(b[0])
       if ts>10**14:ts//=1000 # Binance public files may use microseconds.
       rows.append([datetime.datetime.fromtimestamp(ts/1000,datetime.timezone.utc).isoformat(),*b[1:6]])
   except (urllib.error.HTTPError,urllib.error.URLError,zipfile.BadZipFile) as exc:
    raise RuntimeError(f'Failed historical Binance archive {url}: {exc}') from exc
   day+=datetime.timedelta(days=1)
  target=root/(symbol+'.csv')
  with target.open('w',newline='') as file:
   writer=csv.writer(file);writer.writerow(['timestamp','open','high','low','close','volume']);writer.writerows(rows)
  print(symbol,len(rows),flush=True)
  if len(rows)<days*20:raise RuntimeError(f'Insufficient bars for {symbol}: {len(rows)}')
def load():
 pairs={}
 for f in Path('crypto-agent/data').glob('*.csv'):
  with f.open() as handle:
   rows=list(csv.DictReader(handle))
  if len(rows)<100:continue
  pairs[f.stem]={r['timestamp']:{k:float(r[k]) for k in ('open','high','low','close','volume')} for r in rows}
 return pairs
def run(pairs,name,start,end):
 cash=200.;positions={};trades=[];history={s:[] for s in pairs};last={}
 day='';day_base=200.;halt=False;halts=0;peak=200.;drawdown=0.
 weekly_closed=[];weekly_scale=1.;week_key=None;weekly_reviews=[]
 cost=FEE+SPREAD/2+SLIP
 limits={'conservadora':(2,.20),'adaptativa':(3,.30),'agresiva':(4,.40)}
 max_open,max_exposure=limits[name]
 times=sorted({t for p in pairs.values() for t in p if start<=t<end})
 for t in times:
  bars={s:p[t] for s,p in pairs.items() if t in p}
  # Weekly walk-forward adjustment: use only trades closed before this bar.
  week=datetime.date.fromisoformat(t[:10]).isocalendar()[:2]
  if week!=week_key:
   if week_key is not None:
    recent=[pnl for closed_at,pnl in weekly_closed if closed_at<t and (datetime.date.fromisoformat(t[:10])-datetime.date.fromisoformat(closed_at[:10])).days<=28]
    # Reduce size after a negative rolling 28-day outcome; never increase beyond baseline.
    weekly_scale=.5 if len(recent)>=5 and sum(recent)<0 else 1.
    weekly_reviews.append({'week':str(week),'closed_trades':len(recent),'risk_scale':weekly_scale})
   week_key=week
  # Only past completed candles are in history when decisions are made.
  mark=lambda: cash+sum(p['qty']*(bars[s]['open'] if s in bars else last.get(s,p['entry'])) for s,p in positions.items())
  equity=mark()
  if t[:10]!=day:day=t[:10];day_base=equity;halt=False
  if not halt and equity<=day_base*(1-MAX_DAILY_LOSS):halt=True;halts+=1
  for s,p in list(positions.items()):
   if s not in bars:continue
   bar=bars[s];p['age']+=1
   # Gap at open; otherwise pessimistic stop-first ordering for ambiguous bars.
   px=None
   if bar['open']<=p['stop']:px=bar['open']
   elif bar['open']>=p['target']:px=bar['open']
   elif bar['low']<=p['stop']:px=p['stop']
   elif bar['high']>=p['target']:px=p['target']
   elif p['age']>=72:px=bar['close']
   if px is not None:
    received=p['qty']*px*(1-cost)
    cash+=received;trades.append(received-p['cost']);weekly_closed.append((t,received-p['cost']));del positions[s]
   else:
    # Trailing stop updated after this bar, effective next bar.
    if bar['high']>=p['entry']*(1+p['trail_trigger']):
     p['next_stop']=max(p['stop'],bar['close']*(1-p['distance']))
  for p in positions.values():
   if 'next_stop' in p:p['stop']=p.pop('next_stop')
  equity=mark()
  if not halt and equity<=day_base*(1-MAX_DAILY_LOSS):halt=True;halts+=1
  if halt:
   # Circuit breaker liquidates at available open, not an imaginary stop price.
   for s,p in list(positions.items()):
    if s in bars:
     received=p['qty']*bars[s]['open']*(1-cost)
     cash+=received;trades.append(received-p['cost']);weekly_closed.append((t,received-p['cost']));del positions[s]
  candidates=[]
  for s,b in bars.items():
   h=history[s]
   if len(h)<168 or s in positions or b['volume']<=0:continue
   fast=statistics.fmean(h[-24:]);slow=statistics.fmean(h[-168:])
   vol=statistics.pstdev(h[-48:])/max(statistics.fmean(h[-48:]),1e-9)
   momentum=h[-1]/h[-7]-1
   trend=fast>slow and h[-1]>fast
   if name=='conservadora':
    signal=trend and momentum>.002 and h[-1]>h[-2]
   elif name=='adaptativa':
    signal=(trend and momentum>0) or (abs(fast/slow-1)<.008 and h[-2]<fast<h[-1])
   else:
    signal=trend and h[-1]>=max(h[-24:]) and momentum>.003
   if signal and vol>.002:candidates.append((momentum,s,vol))
  if not halt:
   for _,s,vol in sorted(candidates,reverse=True):
    if len(positions)>=max_open:break
    distance=max(.012,min(.04,vol*1.5))
    # Gross target includes both execution costs and >=1% net target.
    target=max(MIN_NET_TARGET+2*cost,MIN_REWARD_RISK*distance+2*cost)
    equity=mark()
    used=sum(p['cost'] for p in positions.values())
    allocation=min(cash,max(0,200*max_exposure-used),max(0,equity)*MAX_RISK_PER_TRADE*weekly_scale/(distance+2*cost))
    if allocation<5:continue
    px=bars[s]['open'];qty=allocation/(px*(1+cost))
    positions[s]={'qty':qty,'cost':allocation,'entry':px,'stop':px*(1-distance),'target':px*(1+target),'distance':distance,'trail_trigger':target*.5,'age':0}
    cash-=allocation
  for s,b in bars.items():
   last[s]=b['close'];h=history[s];h.append(b['close'])
   if len(h)>168:h.pop(0)
  equity=cash+sum(p['qty']*last.get(s,p['entry']) for s,p in positions.items())
  peak=max(peak,equity);drawdown=max(drawdown,1-equity/peak)
 equity=cash+sum(p['qty']*last.get(s,p['entry']) for s,p in positions.items())
 return {'strategy':name,'initial_usdt':200,'final_usdt':round(equity,3),'return_pct':round(100*(equity/200-1),3),'trades':len(trades),'max_drawdown_pct':round(drawdown*100,3),'halts':halts,'weekly_reviews':weekly_reviews,'realized_pnl':round(sum(trades),3)}
if __name__=='__main__':
 download()
 pairs=load()
 dates=sorted({t for p in pairs.values() for t in p})
 if len(dates)<24*70:raise RuntimeError('Insuficientes datos históricos')
 split=dates[-24*30]
 report={'pairs':list(pairs),'split':split,'training':[],'holdout':[],'disclaimer':'Backtest aproximado, no modela libro de órdenes ni ejecuciones parciales.'}
 for n in PROFILES:
  report['training'].append(run(pairs,n,dates[0],split))
  report['holdout'].append(run(pairs,n,split,dates[-1]+'z'))
 print(json.dumps(report,indent=2))
 Path('crypto-agent/report.json').write_text(json.dumps(report,indent=2))
