"""Per-specialist calibration drift detection and guarded candidate recalibration.
Uses only fully matured shadow labels, never future observations at decision time.
"""
from math import log,exp
from statistics import mean

def sigmoid(x):
    return 1/(1+exp(-max(-30,min(30,x))))

def score(model,sample):
    weights=model["weights"]
    return sigmoid(weights[0]+weights[1]*sample["imbalance"]+
                   weights[2]*sample["spread"]*100)

def fit_model(rows,epochs=200):
    if len(rows)<40:return None
    weights=[0.,0.,0.]
    for _ in range(epochs):
        gradient=[0.,0.,0.]
        for r in rows:
            x=[1.,r["imbalance"],r["spread"]*100]
            error=sigmoid(sum(w*v for w,v in zip(weights,x)))-r["label"]
            for i in range(3):gradient[i]+=error*x[i]
        for i in range(3):
            weights[i]-=.08*(gradient[i]/len(rows)+(.02*weights[i] if i else 0))
    return {"weights":weights}

def calibration_report(model,rows,min_samples=30,drift_margin=.04):
    if model is None or len(rows)<min_samples:
        return {"ready":False,"reason":"insufficient_validation_samples","samples":len(rows)}
    probabilities=[score(model,r) for r in rows]
    base_rate=mean(r["label"] for r in rows)
    brier=mean((p-r["label"])**2 for p,r in zip(probabilities,rows))
    constant=mean((base_rate-r["label"])**2 for r in rows)
    error=abs(mean(probabilities)-base_rate)
    return {"ready":True,"samples":len(rows),"brier":brier,
            "constant_brier":constant,"calibration_error":error,
            "drift":error>drift_margin or brier>constant,
            "beats_constant":brier<constant}

def recalibrate_candidate(train_rows,validation_rows):
    candidate=fit_model(train_rows)
    report=calibration_report(candidate,validation_rows)
    if not report["ready"] or not report["beats_constant"]:
        return {"promote":False,"model":candidate,"validation":report,
                "reason":"failed_independent_calibration"}
    return {"promote":False,"model":candidate,"validation":report,
            "reason":"candidate_requires_frozen_champion_comparison"}

def specialist_reports(groups,models):
    return {name:calibration_report(models.get(name),rows)
            for name,rows in groups.items()}
