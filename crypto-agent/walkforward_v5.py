"""Walk-forward training, calibration and final OOS paper backtest."""
import json
import hashlib
from pathlib import Path
from backtest_v2 import load_data
from labels_v5 import label_opportunities
from meta_v5 import train
from diagnostics_v5 import calibration_diagnostics
from labels_v5 import purged_split
from backtest_v5 import run
from champion_v5 import metrics,evaluate
from memory_reuse_v5 import previous_weights

def validate(data,train_days=45,cal_days=15,test_days=15):
    times=sorted(set().union(*(set(v) for v in data.values())))
    day=288
    if len(times)<day*(train_days+cal_days+test_days):
        raise ValueError("Insufficient 5m history for independent train/cal/test")
    # Hash the exact OHLCV dataset to prevent comparing incompatible market histories.
    digest=hashlib.sha256()
    for symbol in sorted(data):
        for timestamp in sorted(data[symbol]):
            bar=data[symbol][timestamp]
            digest.update(json.dumps([symbol,timestamp,bar["open"],bar["high"],bar["low"],bar["close"],bar["volume"]],separators=(",",":")).encode())
    data_fingerprint=digest.hexdigest()
    rows=label_opportunities(data)
    results=[]
    for i in range(day*(train_days+cal_days),len(times)-day*test_days+1,day*test_days):
        train_end=times[i-day*cal_days]
        cal_end=times[i]
        test_end=times[i+day*test_days-1]
        archived=previous_weights(train_end)
        models,counts=train(rows,train_end,cal_end,test_end,archived=archived)
        _,calibration_rows,test_rows=purged_split(rows,train_end,cal_end,test_end)
        result=run(data,start=cal_end,end=test_end,models=models,
                   entry_threshold=counts["selected_threshold"])
        results.append({"train_end":train_end,"cal_end":cal_end,"test_end":test_end,
                        "samples":counts,"specialists":list(models),
                        "warm_start_sources":{name:models[name].get("warm_start_run") for name in models},
                        "specialist_performance":result["specialist_performance"],
                        "calibration_edge_diagnostics":{name:{
                            "mean_net_return":m["calibration_net_mean"],
                            "return_standard_error":m["return_standard_error"],
                            "calibration_error":m["calibration_error"]}
                            for name,m in models.items()},
                        "entry_threshold":counts["selected_threshold"],
                        "model_snapshots":{name:{"weights":list(m["model"]),
                          "calibration":list(m["calibration"]),
                          "average_win":m["win"],"average_loss":m["loss"],
                          "feature_count":len(m["model"])}
                          for name,m in models.items()},
                        "calibration_by_specialist":calibration_diagnostics(calibration_rows,models),
                        "test_diagnostics_by_specialist":calibration_diagnostics(test_rows,models),
                        "selection_reasons":result["selection_reasons"],
                        "expectation_distribution":result["expectation_distribution"],
                        "baseline_comparison":{name:{"model_brier":m["model_brier"],
                          "constant_brier":m["constant_brier"]} for name,m in models.items()},
                        "final_equity":result["final_equity"],
                        "return_pct":100*(result["final_equity"]/result["initial"]-1),
                        "fees":result["fees"],"fills":result["fills"],
                        "signals":result["signals"]})
    report={"data_fingerprint":data_fingerprint,
            "method":"expanding purged training, independent calibration and disjoint OOS",
            "folds":results,"no_live_orders":True}
    report["champion_candidate_metrics"]=metrics(report)
    report["target_90d_pct"]=5.0
    report["target_gap_pct_points"]=5.0-report["champion_candidate_metrics"]["return_pct"]
    report["target_met"]=report["target_gap_pct_points"]<=0
    report["champion_decision"]=evaluate(report)
    return report

def main():
    report=validate(load_data())
    Path("crypto-agent/audit_v5_walkforward.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
