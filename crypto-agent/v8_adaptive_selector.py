"""Causal, paper-only regime classification and per-symbol strategy routing."""
from statistics import mean, pstdev

def classify(bars, end, window=48):
    """Use only completed candles strictly before index end."""
    if end < max(window, 24):
        return "unknown"
    recent = bars[end-window:end]
    closes = [float(b["close"]) for b in recent]
    if min(closes) <= 0:
        return "unknown"
    returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
    volatility = pstdev(returns) if len(returns)>1 else 0.
    direction = closes[-1]/closes[0]-1
    if volatility > .025:
        return "high_volatility"
    if abs(direction) < max(.006, volatility*4):
        return "range"
    return "uptrend" if direction > 0 else "downtrend"

def select(symbol, regime, candidates, historical_scores=None, min_trades=20):
    """Prefer validated per-asset, per-regime evidence; abstain otherwise.

    Historical scores must be computed strictly before the decision cutoff.
    No implicit global fallback, and no lookahead into final test results.
    """
    scores = historical_scores or {}
    eligible = []
    for candidate in candidates:
        key = (symbol, regime, candidate["id"])
        record = scores.get(key, {})
        if record.get("trades", 0) < min_trades:
            continue
        if record.get("net_return_pct", 0) <= 0:
            continue
        if record.get("max_drawdown_pct", 100) > 12:
            continue
        eligible.append((record["net_return_pct"], candidate["id"], candidate))
    return sorted(eligible, key=lambda x: (-x[0], x[1]))[0][2] if eligible else None
