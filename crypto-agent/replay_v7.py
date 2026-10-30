"""V7 offline event replay. No network, no exchange orders, no Render.
Input JSONL: {"timestamp_ms": ..., "symbol":"BTCUSDT","bid":...,"ask":...,"bid_qty":...,"ask_qty":...}.
Quotes are replayed in time order. Models are trained only on completed earlier labels.
"""
import argparse,json
from pathlib import Path
from statistics import mean
from event_engine_v7 import EventPaperAgent,BookEvent
from event_learning_v7 import build_shadow_labels,purged_time_split
from calibration_v7 import recalibrate_candidate,score
from benchmarks_v7 import compare

def replay(quotes,fee=.001,horizon_ms=60000):
    quotes=sorted(quotes,key=lambda q:(q["timestamp_ms"],q["symbol"]))
    if len(quotes)<120:raise ValueError("Need at least 120 quote events")
    # Strict chronological partitions, with labels purged across boundaries.
    a=quotes[len(quotes)*6//10]["timestamp_ms"]
    b=quotes[len(quotes)*8//10]["timestamp_ms"]
    last=quotes[-1]["timestamp_ms"]+1
    records=[{"kind":"book_ticker","timestamp_ms":q["timestamp_ms"],"symbol":q["symbol"],
              "payload":{k:q[k] for k in ("bid","ask","bid_qty","ask_qty")}} for q in quotes]
    labels=build_shadow_labels(records,horizon_ms=horizon_ms,fee=fee)
    train,cal,test=purged_time_split(labels,a,b,last)
    candidate=recalibrate_candidate(train,cal)
    model=candidate["model"] if candidate["validation"].get("beats_constant") else None
    agent=EventPaperAgent(fee=fee)
    open_since={};outcomes=[]
    # Use fixed calibrated conditional returns, not future test outcomes.
    wins=[r["net_return"] for r in train if r["label"]]
    losses=[-r["net_return"] for r in train if not r["label"]]
    avg_win=mean(wins) if wins else 0.
    avg_loss=mean(losses) if losses else 0.
    for q in quotes:
        t=q["timestamp_ms"]
        if t<b:continue
        event=BookEvent(t,q["symbol"],q["bid"],q["ask"],q["bid_qty"],q["ask_qty"])
        if q["symbol"] in open_since and t-open_since[q["symbol"]]>=horizon_ms:
            held=agent.portfolio.positions.get(q["symbol"],0)
            if held>0:
                oid=f"exit:{q['symbol']}:{t}"
                agent.portfolio.place(oid,q["symbol"],"sell",held)
                before=agent.portfolio.realized_pnl
                agent.portfolio.execute(oid,held,q["bid"],fee)
                outcomes.append({"symbol":q["symbol"],"exit_ms":t,
                                 "realized_pnl":agent.portfolio.realized_pnl-before})
            del open_since[q["symbol"]]
        if model is None:continue
        sample={"imbalance":(q["bid_qty"]-q["ask_qty"])/max(1e-9,q["bid_qty"]+q["ask_qty"]),
                "spread":(q["ask"]-q["bid"])/((q["ask"]+q["bid"])/2)}
        p=score(model,sample)
        expected=p*avg_win-(1-p)*avg_loss
        # This is already a NET label forecast. Avoid double charging fees in the gate.
        if expected<.002:continue
        if q["symbol"] in open_since:continue
        fill=agent.on_book(event,expected+sample["spread"]+2*fee,now_ms=t)
        if fill is not None:open_since[q["symbol"]]=t
    last_prices={q["symbol"]:q["bid"] for q in quotes}
    equity=agent.portfolio.equity(last_prices)
    return {"status":"evaluated","source":"event_quote_replay","model_enabled":model is not None,
            "calibration":candidate["validation"],"sample_counts":{"train":len(train),"cal":len(cal),"test":len(test)},
            "benchmarks":{"calibration":compare(cal),"test":compare(test)},
            "initial_equity":200.,"final_equity":equity,
            "return_pct":(equity/200.-1)*100,"entries":len([f for f in agent.portfolio.fills if f.side=="buy"]),
            "exits":len(outcomes),"fees":agent.portfolio.fees_paid,
            "realized_pnl":agent.portfolio.realized_pnl,
            "open_positions":{s:q for s,q in agent.portfolio.positions.items() if q>0},
            "no_real_orders":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--quotes",required=True)
    parser.add_argument("--output",default="crypto-agent/v7-replay-results.json")
    args=parser.parse_args()
    with open(args.quotes) as f:quotes=[json.loads(line) for line in f if line.strip()]
    result=replay(quotes)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
