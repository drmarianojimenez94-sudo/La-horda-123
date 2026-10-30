import csv, json, math, statistics, urllib.request, datetime, time
from pathlib import Path
PROFILES={'conservadora':(10,3,.01,-1.6,.006,.018),'agresiva':(30,5,.03,-1.05,.011,.035),'adaptativa':(20,4,.02,-1.3,.008,.024)}
FEE=.001; SPREAD=.0006; SLIP=.0005
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CryptoAgentPaper/1.0'}),timeout=20) as r:return json.load(r)
def download(days=90,top=20):
 root=Path('crypto-agent/data');root.mkdir(parents=True,exist_ok=True)
 info=get('https://api.binance.com/api/v3/exchangeInfo')
 allowed={s['symbol'] for s in info['symbols'] if s['status']=='TRADING' and s['quoteAsset']=='USDT' and s.get('isSpotTradingAllowed',True) and s['baseAsset'] not in {'USDC','FDUSD','TUSD','DAI','USDE','USD1'} and not s['baseAsset'].endswith(('UP','DOWN','BULL','BEAR'))}
 ticks=get('https://api.binance.com/api/v3/ticker/24hr')
 names=[x['symbol'] for x in sorted((x for x in ticks if x['symbol'] in allowed),key=lambda x:float(x['quoteVolume']),reverse=True)[:top]]
 end=int(time.time()*1000);start=end-days*86400000
 for symbol in names:
  cursor=start;rows=[]
  while cursor<end:
   batch=get(f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&startTime={cursor}&endTime={end}&limit=1000')
   if not batch:break
   for b in batch:
    if b[6]<end-3600000:rows.append([datetime.datetime.fromtimestamp(b[0]/1000,datetime.timezone.utc).isoformat(),*b[1:6]])
   cursor=int(batch[-1][0])+3600000
   time.sleep(.12)
  with (root/(symbol+'.csv')).open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['timestamp','open','high','low','close','volume']);w.writerows(rows)
  print(symbol,len(rows),flush=True)
def load():
 pairs={}
 for f in Path('crypto-agent/data').glob('*.csv'):
  with f.open() as handle:
   rows=list(csv.DictReader(handle))
  if len(rows)<100:continue
  pairs[f.stem]={r['timestamp']:{k:float(r[k]) for k in ('open','high','low','close','volume')} for r in rows}
 return pairs
def run(pairs,name,start,end):
 size,max_open,loss,zlim,tp,stop=PROFILES[name];cash=200.;positions={};trades=[];history={s:[] for s in pairs};last={};day='';base=200.;halt=False;halts=0;peak=200.;drawdown=0
 times=sorted({t for p in pairs.values() for t in p if start<=t<end})
 for t in times:
  bars={s:p[t] for s,p in pairs.items() if t in p}
  for s,b in bars.items():last[s]=b['close']
  equity=cash+sum(p['qty']*last.get(s,p['entry']) for s,p in positions.items())
  if t[:10]!=day:day=t[:10];base=equity;halt=False
  if not halt and equity<=base*(1-loss):halt=True;halts+=1
  for s,p in list(positions.items()):
   if s not in bars:continue
   px=bars[s]['open'];p['age']+=1
   if px>=p['entry']*(1+tp) or px<=p['entry']*(1-stop) or p['age']>=72:
    received=p['qty']*px*(1-SPREAD/2-SLIP)*(1-FEE)
    cash+=received;trades.append(received-p['cost']);del positions[s]
  candidates=[]
  for s,b in bars.items():
   h=history[s]
   if len(h)==48 and s not in positions and b['volume']>0:
    mean=statistics.fmean(h);sd=statistics.pstdev(h)
    if sd>0 and sd/mean>.002:
     z=(h[-1]-mean)/sd
     if z<zlim:candidates.append((z,s,sd/mean))
  if not halt:
   for _,s,vol in sorted(candidates):
    if len(positions)>=max_open:break
    allocation=size*(.5 if name=='adaptativa' and vol>.025 else 1)
    if cash<allocation:continue
    px=bars[s]['open']*(1+SPREAD/2+SLIP)
    qty=allocation/(px*(1+FEE))
    positions[s]={'qty':qty,'cost':allocation,'entry':bars[s]['open'],'age':0};cash-=allocation
  for s,b in bars.items():
   h=history[s];h.append(b['close'])
   if len(h)>48:h.pop(0)
  equity=cash+sum(p['qty']*last.get(s,p['entry']) for s,p in positions.items())
  peak=max(peak,equity);drawdown=max(drawdown,1-equity/peak)
 equity=cash+sum(p['qty']*last.get(s,p['entry']) for s,p in positions.items())
 return {'strategy':name,'initial_usdt':200,'final_usdt':round(equity,3),'return_pct':round(100*(equity/200-1),3),'trades':len(trades),'max_drawdown_pct':round(drawdown*100,3),'halts':halts}
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
