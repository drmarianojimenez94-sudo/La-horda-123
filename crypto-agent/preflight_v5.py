"""Fast fail-closed feasibility check before expensive V5 walk-forward.
This is NOT a profitability guarantee; never trains on future test labels.
"""
import json
from pathlib import Path
from backtest_v2 import load_data
from labels_v5 import label_opportunities,purged_split
from meta_v5 import train,select

def preflight(data,train_days=45,cal_days=15,test_days=15):
    times=sorted(set().union(*(set(v) for v in data.values())))
    day=288
    if len(times)<day*(train_days+cal_days+test_days):
        return {"ready":False,"reason":"insufficient_history","bars":len(times)}
    rows=label_opportunities(data,step=12)
    train_end=times[day*train_days]
    cal_end=times[day*(train_days+cal_days)]
    test_end=times[min(len(times)-1,day*(train_days+cal_days+test_days)-1)]
    models,counts=train(rows,train_end,cal_end,test_end)
    _,calibration,_=purged_split(rows,train_end,cal_end,test_end)
    # Feasibility only on calibration rows, never test outcomes.
    calibrated_signals=[{"symbol":r["symbol"],**r} for r in calibration]
    eligible=sum(bool(select([r],models,threshold=counts["selected_threshold"])) for r in calibrated_signals)
    return {"ready":bool(models) and eligible>0,"models":list(models),
            "calibration_eligible_signals":eligible,"samples":counts,
            "entry_threshold":counts["selected_threshold"],
            "reason":"ok" if eligible else "no_positive_expectancy_calibration_signals"}

def main():
    result=preflight(load_data())
    path=Path("crypto-agent/preflight_v5.json")
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not result["ready"]:
        raise SystemExit("V5 preflight failed: inspect preflight_v5.json; skipping expensive backtest")

if __name__=="__main__":main()
