"""Explain every candidate rejection without changing live risk thresholds."""
from statistics import mean
from learner_v4 import predict
from v4_extension import calibrated_probability

def diagnose(signals,models,exposure=None,limit=.4,per_asset=.15,threshold=.0018):
    exposure=dict(exposure or {})
    decisions=[]
    for row in signals:
        name=row["strategy"];symbol=row["symbol"]
        m=models.get(name)
        result={"symbol":symbol,"strategy":name,"reason":None,"threshold":threshold,
                "probability":None,"expected_net":None}
        if m is None:
            result["reason"]="specialist_unavailable"
        else:
            p=calibrated_probability(predict(m["model"],row),m["calibration"])
            expected=p*m["win"]-(1-p)*m["loss"]
            penalty=sum(exposure.values())*.25*m["loss"]
            uncertainty=(.25*m.get("calibration_error",0)*(m["win"]+m["loss"])
                         +.25*m.get("return_standard_error",0)+.0001)
            result.update(probability=p,expected_net=expected-penalty-uncertainty,
                          gross_expected=expected,portfolio_penalty=penalty,
                          uncertainty_buffer=uncertainty)
            if expected-penalty-uncertainty<threshold:
                result["reason"]="insufficient_expected_net"
            elif symbol in exposure:
                result["reason"]="existing_asset_exposure"
            elif len(exposure)>=3 or sum(exposure.values())>=limit:
                result["reason"]="portfolio_capacity"
            else:
                allocation=min(per_asset,limit-sum(exposure.values()))
                exposure[symbol]=allocation
                result.update(reason="accepted",allocation_fraction=allocation)
        decisions.append(result)
    return decisions

def calibration_diagnostics(rows,models):
    output={}
    for name in ("trend","breakout","mean_reversion"):
        subset=[r for r in rows if r["strategy"]==name]
        m=models.get(name)
        if not subset:
            output[name]={"samples":0,"status":"no_samples"}
            continue
        if m is None:
            output[name]={"samples":len(subset),"status":"unavailable"}
            continue
        probabilities=[calibrated_probability(predict(m["model"],r),m["calibration"]) for r in subset]
        observed=[int(r["label"]) for r in subset]
        output[name]={"samples":len(subset),"status":"calibrated",
                      "brier":mean((p-y)**2 for p,y in zip(probabilities,observed)),
                      "base_rate":mean(observed),
                      "mean_probability":mean(probabilities)}
    return output
