"""Offline research meta-model. Fit only on purged historical labels."""
from statistics import mean,pstdev
from learner_v4 import fit, predict
from v4_extension import fit_platt, calibrated_probability
from labels_v5 import purged_split

def train(rows, train_end, calibration_end, test_end, archived=None):
    training, calibration, test = purged_split(rows, train_end, calibration_end, test_end)
    models = {}
    archived=archived or {}
    for name in ("trend", "breakout", "mean_reversion"):
        train_rows = [r for r in training if r["strategy"] == name]
        cal_rows = [r for r in calibration if r["strategy"] == name]
        prior=archived.get(name)
        model = fit(train_rows, min_samples=30,
                    initial_weights=prior["weights"] if prior else None)
        if model is None or len(cal_rows) < 30:
            continue
        calibration_model = fit_platt(
            [predict(model, r) for r in cal_rows],
            [r["label"] for r in cal_rows])
        if calibration_model is None:
            continue
        wins = [r["net_return"] for r in train_rows if r["net_return"] > 0]
        losses = [-r["net_return"] for r in train_rows if r["net_return"] < 0]
        if not wins or not losses:
            continue
        probabilities=[calibrated_probability(predict(model,r),calibration_model) for r in cal_rows]
        base_rate=sum(r["label"] for r in train_rows)/len(train_rows)
        model_brier=mean((p-r["label"])**2 for p,r in zip(probabilities,cal_rows))
        constant_brier=mean((base_rate-r["label"])**2 for r in cal_rows)
        if model_brier>=constant_brier:
            continue  # reject specialist that cannot beat a constant predictor
        # Historical opportunities overlap in time; discount effective sample size.
        cal_returns=[float(r["net_return"]) for r in cal_rows]
        effective_n=max(1,len(cal_returns)//12)
        uncertainty=pstdev(cal_returns)/(effective_n**.5)
        models[name] = {"model": model, "calibration": calibration_model,
                        "calibration_net_mean":mean(cal_returns),
                        "return_standard_error":uncertainty,
                        "model_brier":model_brier,"constant_brier":constant_brier,
                        "win": mean(wins), "loss": mean(losses),
                        "calibration_samples":len(cal_rows),
                        "calibration_error":abs(mean(probabilities)-mean(r["label"] for r in cal_rows)),
                        "warm_start_run":prior["source_run"] if prior else None}
    # Select a conservative entry threshold using calibration only, never OOS.
    # Positive expectancy is mandatory; cap the historical fixed threshold at 0.18%.
    positive=[]
    for row in calibration:
        m=models.get(row["strategy"])
        if m is None:continue
        p=calibrated_probability(predict(m["model"],row),m["calibration"])
        uncertainty=.25*m["calibration_error"]*(m["win"]+m["loss"])+.25*m["return_standard_error"]
        edge=p*m["win"]-(1-p)*m["loss"]-uncertainty-.0001
        if edge>0:positive.append(edge)
    positive.sort()
    threshold=max(.0001,min(.0018,positive[int(.75*(len(positive)-1))])) if positive else .0018
    return models, {"train": len(training), "calibration": len(calibration),
                    "test": len(test), "calibration_positive":len(positive),
                    "selected_threshold":threshold,
                    "threshold_method":"positive_calibration_edge_75th_percentile"}

def select(signals, models, exposure=None, limit=.4, per_asset=.15, threshold=.0018):
    exposure = dict(exposure or {})
    ranked = []
    for signal in signals:
        model = models.get(signal["strategy"])
        if model is None:
            continue
        probability = calibrated_probability(
            predict(model["model"], signal), model["calibration"])
        expected = probability * model["win"] - (1-probability) * model["loss"]
        expected -= sum(exposure.values()) * .25 * model["loss"]
        expected -= (.25*model.get("calibration_error",0)*(model["win"]+model["loss"])
                     +.25*model.get("return_standard_error",0)+.0001)
        if expected >= threshold:
            ranked.append((expected, signal, probability))
    ranked.sort(key=lambda row: row[0], reverse=True)
    selected = []
    for expected, signal, probability in ranked:
        symbol = signal["symbol"]
        if symbol in exposure or len(exposure) >= 3:
            continue
        allocation = min(per_asset, max(0., limit-sum(exposure.values())))
        if allocation <= 0:
            break
        exposure[symbol] = allocation
        selected.append({**signal, "expected_net": expected,
                         "probability": probability,
                         "allocation_fraction": allocation})
    return selected
