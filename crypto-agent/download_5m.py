"""Download historical 5-minute Binance spot candles for research."""
import csv
import datetime
import io
import urllib.request
import zipfile
from pathlib import Path

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT", "AVAXUSDT")

def download(days=90,symbols=SYMBOLS):
    end = datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=days - 1)
    folder = Path("crypto-agent/data_5m")
    folder.mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        count = 0
        with (folder / (symbol + ".csv")).open("w", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trade_count", "taker_buy_base", "taker_buy_quote"])
            for offset in range(days):
                day = start + datetime.timedelta(days=offset)
                filename = symbol + "-5m-" + day.isoformat() + ".zip"
                url = "https://data.binance.vision/data/spot/daily/klines/" + symbol + "/5m/" + filename
                with urllib.request.urlopen(url, timeout=40) as response:
                    archive = response.read()
                with zipfile.ZipFile(io.BytesIO(archive)) as z:
                    with z.open(z.namelist()[0]) as source:
                        for row in csv.reader(io.TextIOWrapper(source, encoding="utf-8-sig")):
                            if not row or not row[0].isdigit():
                                continue
                            stamp = int(row[0])
                            if stamp > 10**14:
                                stamp //= 1000
                            ts = datetime.datetime.fromtimestamp(stamp / 1000, datetime.timezone.utc).isoformat()
                            writer.writerow([ts, *row[1:6], row[7], row[8], row[9], row[10]])
                            count += 1
        if count < days * 250:
            raise RuntimeError("Insufficient candles for " + symbol)
        print(symbol, count, flush=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, choices=(90, 180, 365), default=90)
    parser.add_argument("--symbols",default=",".join(SYMBOLS))
    args=parser.parse_args()
    symbols=tuple(x.strip().upper() for x in args.symbols.split(",") if x.strip())
    if not symbols or any(x not in SYMBOLS for x in symbols):
        parser.error("Symbols must be in the supported spot symbol list")
    download(args.days,symbols)
