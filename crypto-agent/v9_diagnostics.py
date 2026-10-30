"""V9 causal diagnostics: descriptive research only, never live trading."""
from collections import defaultdict
from statistics import mean

def classify_regime(bars, end, lookback=288):
    """Use completed candles strictly before end; no future leakage."""
    if end < lookback or lookback < 2:
        return "insufficient_history"
    window = bars[end-lookback:end]
    first, last = window[0]["close"], window[-1]["close"]
    if first <= 0:
        return "invalid_data"
    change = last / first - 1
    if change >= .03:
        return "bull"
    if change <= -.03:
        return "bear"
    return "sideways"

def walk_forward_regimes(bars, start, end, step=288, lookback=288):
    if step <= 0:
        raise ValueError("step must be positive")
    return [{"start": i, "end": min(i+step, end),
             "regime": classify_regime(bars, i, lookback)}
            for i in range(max(start,lookback), end, step)]

def trade_attribution(journal, initial_cash):
    """Attribute realized PnL and execution costs from actual ledger fills."""
    entries = defaultdict(list)
    trades = []
    for fill in journal:
        symbol = fill["symbol"]
        if fill["kind"] == "buy":
            entries[symbol].append(fill)
        elif fill["kind"] == "sell":
            if not entries[symbol]:
                raise ValueError("Sell without matching buy")
            entry = entries[symbol].pop(0)
            qty = entry["qty"]
            if abs(qty-fill["qty"]) > 1e-8:
                raise ValueError("Partial fills require a lot-aware adapter")
            gross_price_pnl = qty * (fill["price"]-entry["price"])
            fees = entry["fee"] + fill["fee"]
            trades.append({"symbol":symbol,"reason":fill.get("reason","unknown"),
                           "gross_price_pnl":gross_price_pnl,"fees":fees,
                           "net_pnl":gross_price_pnl-fees})
    if any(entries.values()):
        raise ValueError("Unclosed fills: supply mark-to-market separately")
    return {"trades":len(trades),"gross_price_pnl":sum(t["gross_price_pnl"] for t in trades),
            "fees":sum(t["fees"] for t in trades),
            "net_pnl":sum(t["net_pnl"] for t in trades),
            "net_return_pct":100*sum(t["net_pnl"] for t in trades)/initial_cash,
            "by_exit_reason":{reason:{"count":sum(t["reason"]==reason for t in trades),
                "net_pnl":sum(t["net_pnl"] for t in trades if t["reason"]==reason)}
                for reason in sorted(set(t["reason"] for t in trades))}}

def causal_prior_weights(prior_runs, cutoff_ms, decay=.8):
    """Prior validation is a research ranking hint, not model training or promotion."""
    if not 0 < decay <= 1:
        raise ValueError("invalid decay")
    eligible = sorted((r for r in prior_runs if r["trained_until_ms"] < cutoff_ms),
                      key=lambda r:r["trained_until_ms"])
    scores, weight = defaultdict(float), defaultdict(float)
    for age, run in enumerate(reversed(eligible)):
        w = decay ** age
        for candidate in run.get("ranked",[]):
            scores[candidate["id"]] += w*candidate["validation_mean_pct"]
            weight[candidate["id"]] += w
    return {key:scores[key]/weight[key] for key in sorted(scores)}

def regime_validation(results, minimum_trades=20):
    """Reject if any observed regime is losing or insufficiently sampled."""
    valid = {r["regime"]:r for r in results if r["regime"] in ("bull","bear","sideways")}
    if not valid:
        return {"approved":False,"reason":"no_regime_validation"}
    failures = [k for k,v in valid.items()
                if v["trades"] < minimum_trades or v["net_return_pct"] <= 0]
    return {"approved":not failures,"reason":"regime_gate_failed" if failures else "passed",
            "failed_regimes":failures,"observed_regimes":sorted(valid)}
