"""Auditable V8 research summary; records cash baseline, selections, costs and rejected variants."""
import json,os
from pathlib import Path
from v8_run_memory import store_run,prior_candidates

def generate(report_path,db_path,out_path,run_id="local",cutoff_ms=0):
    report=json.loads(Path(report_path).read_text())
    prior=prior_candidates(db_path,cutoff_ms)
    digest=store_run(report,db_path,run_id,cutoff_ms)
    chosen=report.get("selected")
    ranked=report.get("ranked",[])
    summary={"run_id":str(run_id),"report_sha256":digest,
      "candidates_evaluated":report.get("tested"),
      "selected":chosen,"rejected_candidates":len(ranked)-int(chosen is not None),
      "cash_return_pct":0.,"prior_valid_runs":len(prior),
      "prior_selected":[x["selected"] for x in prior],
      "test_result":report.get("selected_test_results"),
      "selected_test_mean_return_pct":(sum(x["test"]["return_pct"] for x in report["selected_test_results"].values())/len(report["selected_test_results"]) if report.get("selected_test_results") else None),
      "selected_test_total_fees":(sum(x["test"]["fees"] for x in report["selected_test_results"].values()) if report.get("selected_test_results") else None),
      "top_validation":[{"id":r["id"],"validation_mean_pct":r["validation_mean_pct"],
          "trades":r["validation_trades"],"max_drawdown_pct":r["validation_max_dd_pct"]}
          for r in ranked[:10]],
      "selection_is_validation_only":True,
      "memory_reused_for_training":False,
      "warning":"Archived candidates are compared, but coefficients are not retrained by this workflow."}
    Path(out_path).write_text(json.dumps(summary,indent=2))
    return summary

if __name__=="__main__":
    print(json.dumps(generate("crypto-agent/v8-strategy-research.json",
        "crypto-agent/state/v8-research.sqlite3","crypto-agent/v8-economic-audit.json",
        os.getenv("GITHUB_RUN_ID","local"),int(os.getenv("TRAIN_CUTOFF_MS","0"))),indent=2))
