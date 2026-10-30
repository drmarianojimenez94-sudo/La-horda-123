"""Simple comparison references for matured event observations."""
from statistics import mean

def compare(samples):
    if not samples:
        return {"count":0,"cash_return":0,"all_quotes":None,"imbalance_filter":None}
    all_returns=[s["net_return"] for s in samples]
    subset=[s["net_return"] for s in samples if s["imbalance"]>.2]
    return {"count":len(samples),"cash_return":0,
            "all_quotes":{"mean_return":mean(all_returns),"count":len(all_returns)},
            "imbalance_filter":{"mean_return":mean(subset) if subset else None,
                                "count":len(subset)},
            "note":"Overlapping hypothetical opportunity returns; not portfolio performance"}
