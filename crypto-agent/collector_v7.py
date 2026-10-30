"""Public Binance spot book ticker recorder (paper research only).
WebSocket is optional dependency: pip install websockets.
No exchange API keys, no live orders. Run on a persistent host, not GitHub Actions.
"""
import asyncio,json,os,time
from event_memory_v7 import EventMemory
from event_engine_v7 import BookEvent,features

async def collect(symbols=("btcusdt","ethusdt"),db_path="crypto-agent/state/v7-memory.sqlite3"):
    import websockets
    streams="/".join(f"{s.lower()}@bookTicker" for s in symbols)
    url="wss://stream.binance.com:9443/stream?streams="+streams
    memory=EventMemory(db_path)
    delay=1
    try:
        while True:
            try:
                async with websockets.connect(url,ping_interval=20,ping_timeout=20,max_queue=1000) as ws:
                    delay=1
                    async for raw in ws:
                        packet=json.loads(raw)
                        data=packet.get("data",{})
                        # bookTicker is best bid/ask, NOT full historical L2 depth.
                        event=BookEvent(timestamp_ms=int(time.time()*1000),
                                        symbol=data["s"],bid=float(data["b"]),
                                        ask=float(data["a"]),bid_qty=float(data["B"]),
                                        ask_qty=float(data["A"]))
                        memory.record("book_ticker",event.symbol,
                                      {**features(event),"bid":event.bid,"ask":event.ask,
                                       "bid_qty":event.bid_qty,"ask_qty":event.ask_qty},
                                      event.timestamp_ms)
            except (OSError,ConnectionError,asyncio.TimeoutError,ValueError,KeyError) as error:
                memory.record("connection_error","SYSTEM",{"error":str(error)})
                await asyncio.sleep(delay)
                delay=min(60,delay*2)
    finally:memory.close()

if __name__=="__main__":
    asyncio.run(collect())
