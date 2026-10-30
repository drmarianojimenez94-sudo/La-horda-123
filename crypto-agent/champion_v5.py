"""V5 champion/challenger registry: fail-closed model promotion.
A historical backtest cannot guarantee future performance. Promotion requires
the SAME frozen evaluation cohort and data hash, not merely larger backtest PnL.
"""
import json,hashlib
from pathlib import Path

def fingerprint(report):
    folds=report.get("folds",[])
    return hashlib.sha256(json.dumps([(f.get("cal_end"),f.get("test_end")) for f in folds],
                            sort_keys=True).encode()).hexdigest()

def metrics(report):
    folds=report.get("folds",[])
    if not folds:raise ValueError("Missing out-of-sample folds")
    returns=[float(f["return_pct"])/100 for f in folds]
    if any(x<=-1 for x in returns):raise ValueError("Invalid fold return")
    growth=1.
    for value in returns:growth*=1+value
    equity=1.;peak=1.;drawdown=0.
    for value in returns:
        equity*=1+value;peak=max(peak,equity)
        drawdown=max(drawdown,1-equity/peak)
    return {"return_pct":100*(growth-1),"max_drawdown_pct":100*drawdown,
            "folds":len(folds),"active_folds":sum(int(f.get("fills",0))>0 for f in folds),
            "fees":sum(float(f.get("fees",0)) for f in folds)}

def evaluate(challenger,champion=None,min_active=2,minimum_gain_pct=.25):
    candidate=metrics(challenger)
    if candidate["active_folds"]<min_active:
        return {"promote":False,"reason":"insufficient_active_folds","candidate":candidate}
    if candidate["return_pct"]<=0:
        return {"promote":False,"reason":"nonpositive_oos_return","candidate":candidate}
    if champion is None:
        return {"promote":False,"reason":"no_frozen_champion_benchmark","candidate":candidate}
    current=metrics(champion)
    if fingerprint(challenger)!=fingerprint(champion):
        return {"promote":False,"reason":"noncomparable_oos_windows","candidate":candidate,"champion":current}
    if challenger.get("data_fingerprint")!=champion.get("data_fingerprint") or not challenger.get("data_fingerprint"):
        return {"promote":False,"reason":"unverified_market_data","candidate":candidate,"champion":current}
    if candidate["max_drawdown_pct"]>current["max_drawdown_pct"]+1e-9:
        return {"promote":False,"reason":"higher_drawdown","candidate":candidate,"champion":current}
    if candidate["return_pct"]<current["return_pct"]+minimum_gain_pct:
        return {"promote":False,"reason":"insufficient_improvement","candidate":candidate,"champion":current}
    return {"promote":True,"reason":"passed_comparable_oos_gate","candidate":candidate,"champion":current}

def compare_archive(folder="training-memory/v5/runs"):
    files=sorted(Path(folder).glob("*.json"))
    reports=[]
    for path in files:
        record=json.loads(path.read_text())
        report=record.get("report")
        if not isinstance(report,dict):continue
        try:
            summary=metrics(report)
            reports.append({"run_id":record.get("run_id"),"path":str(path),
                            "fingerprint":fingerprint(report),"metrics":summary})
        except (KeyError,TypeError,ValueError):continue
    return {"runs_examined":len(files),"valid_reports":reports,
            "note":"Historical runs are NOT automatically comparable; champion promotion requires identical frozen OOS windows and data."}

if __name__=="__main__":
    print(json.dumps(compare_archive(),indent=2))
