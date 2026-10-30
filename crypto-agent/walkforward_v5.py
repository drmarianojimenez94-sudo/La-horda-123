"""Walk-forward training, calibration and final OOS paper backtest."""
import json
from pathlib import Path
from backtest_v2 import load_data
from labels_v5 import label_opportunities
from meta_v5 import train
from diagnostics_v5 import calibration_diagnostics
from labels_v5 import purged_split
from backtest_v5 import run

def validate(data,train_days=45,cal_days=15,test_days=15):
    times=sorted(set().union(*(set(v) for v in data.values())))
    day=288
    if len(times)<day*(train_days+cal_days+test_days):
        raise ValueError("Insufficient 5m history for independent train/cal/test")
    rows=label_opportunities(data)
    results=[]
    for i in range(day*(train_days+cal_days),len(times)-day*test_days+1,day*test_days):
        train_end=times[i-day*cal_days]
        cal_end=times[i]
        test_end=times[i+day*test_days-1]
        models,counts=train(rows,train_end,cal_end,test_end)
        _,calibration_rows,test_rows=purged_split(rows,train_end,cal_end,test_end)
        result=run(data,start=cal_end,end=test_end,models=models)
        results.append({"train_end":train_end,"cal_end":cal_end,"test_end":test_end,
                        "samples":counts,"specialists":list(models),
                        "model_snapshots":{name:{"weights":list(m["model"]),
                          "calibration":list(m["calibration"]),
                          "average_win":m["win"],"average_loss":m["loss"]}
                          for name,m in models.items()},
                        "calibration_by_specialist":calibration_diagnostics(calibration_rows,models),
                        "test_diagnostics_by_specialist":calibration_diagnostics(test_rows,models),
                        "selection_reasons":result["selection_reasons"],
                        "final_equity":result["final_equity"],
                        "return_pct":100*(result["final_equity"]/result["initial"]-1),
                        "fees":result["fees"],"fills":result["fills"],
                        "signals":result["signals"]})
    return {"method":"expanding purged training, independent calibration and disjoint OOS",
            "folds":results,"no_live_orders":True}

def main():
    report=validate(load_data())
    Path("crypto-agent/audit_v5_walkforward.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
