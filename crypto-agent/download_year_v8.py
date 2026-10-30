"""Download actual Binance spot monthly 5m OHLCV for calendar year 2025.
Use exchange archives, not generated candles. Fail closed on missing months or gaps.
"""
import argparse,csv,datetime as dt,io,urllib.request,zipfile
from pathlib import Path

FIELDS=["timestamp","open","high","low","close","volume","quote_volume",
        "trade_count","taker_buy_base","taker_buy_quote"]
SYMBOLS=("BTCUSDT","ETHUSDT")
def parse_timestamp(raw):
    stamp=int(raw)
    if stamp>10**14:stamp//=1000
    return dt.datetime.fromtimestamp(stamp/1000,dt.timezone.utc)

def download_year(year=2025,symbols=SYMBOLS,folder="crypto-agent/data_5m"):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    report={}
    for symbol in symbols:
        if symbol not in SYMBOLS:raise ValueError("Unsupported symbol")
        count=0;previous=None;first=None
        with (folder/(symbol+".csv")).open("w",newline="") as output:
            writer=csv.writer(output);writer.writerow(FIELDS)
            for month in range(1,13):
                name=f"{symbol}-5m-{year}-{month:02d}.zip"
                url=f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/5m/{name}"
                with urllib.request.urlopen(url,timeout=120) as response:
                    payload=response.read()
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    with archive.open(archive.namelist()[0]) as raw:
                        for row in csv.reader(io.TextIOWrapper(raw,encoding="utf-8-sig")):
                            if not row or not row[0].isdigit():continue
                            ts=parse_timestamp(row[0])
                            if ts.year!=year:raise ValueError("Unexpected year in exchange archive")
                            if previous and (ts-previous).total_seconds()!=300:
                                raise ValueError(f"Missing or duplicate 5m candle {symbol} {previous} -> {ts}")
                            first=first or ts;previous=ts
                            writer.writerow([ts.isoformat(),*row[1:6],row[7],row[8],row[9],row[10]])
                            count+=1
        expected=(dt.date(year+1,1,1)-dt.date(year,1,1)).days*288
        if count!=expected:raise ValueError(f"{symbol}: expected {expected}, received {count}")
        report[symbol]={"candles":count,"first":first.isoformat(),"last":previous.isoformat()}
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--year",type=int,default=2025)
    args=parser.parse_args()
    print(download_year(args.year),flush=True)
