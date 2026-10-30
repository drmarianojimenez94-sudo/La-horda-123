"""Store and summarize completed paper-trade outcomes without future leakage."""
import json
from event_memory_v7 import EventMemory

def record_outcome(path, symbol, regime, strategy, pnl, exit_ms):
    memory = EventMemory(path)
    try:
        memory.record("strategy_outcome", symbol, {"regime":regime, "strategy":strategy, "pnl":float(pnl)}, exit_ms)
    finally:
        memory.close()

def historical_scores(path, cutoff_ms, capital=200.):
    memory = EventMemory(path)
    try:
        rows = memory.db.execute("SELECT symbol,payload FROM events WHERE kind=? AND observed_ms<?",
                                 ("strategy_outcome", int(cutoff_ms))).fetchall()
    finally:
        memory.close()
    groups = {}
    for symbol, raw in rows:
        event = json.loads(raw)
        key = (symbol, event["regime"], event["strategy"])
        groups.setdefault(key, []).append(event["pnl"])
    return {key: {"trades":len(pnls), "net_return_pct":100*sum(pnls)/capital,
                  "max_drawdown_pct":_drawdown(pnls, capital)} for key,pnls in groups.items()}

def _drawdown(pnls, capital):
    equity = peak = float(capital)
    dd = 0.
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        dd = max(dd, 100*(peak-equity)/peak)
    return dd
