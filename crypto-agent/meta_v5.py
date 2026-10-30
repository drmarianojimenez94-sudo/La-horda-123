"""Offline research meta-model. Fit only on purged historical labels."""
from statistics import mean
from learner_v4 import fit, predict
from v4_extension import fit_platt, calibrated_probability
from labels_v5 import purged_split

def train(rows, train_end, calibration_end, test_end):
    training, calibration, test = purged_split(rows, train_end, calibration_end, test_end)
    models = {}
    for name in ("trend", "breakout", "mean_reversion"):
        train_rows = [r for r in training if r["strategy"] == name]
        cal_rows = [r for r in calibration if r["strategy"] == name]
        model = fit(train_rows, min_samples=30)
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
        models[name] = {"model": model, "calibration": calibration_model,
                        "model_brier":model_brier,"constant_brier":constant_brier,
                        "win": mean(wins), "loss": mean(losses)}
    return models, {"train": len(training), "calibration": len(calibration),
                    "test": len(test)}

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
