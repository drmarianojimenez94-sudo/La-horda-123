"""Causal regularized logistic learner fitted on completed historical trades only.
Pure Python; no remote model, no live orders, no dependency on scikit-learn.
"""
import math

FEATURES=("bias","trend","breakout","reversion","bull","sideways","bear","stop","reward")
def vector(row):
    strategy=row.get("strategy")
    regime=row.get("regime")
    return (1.0,float(strategy=="trend"),float(strategy=="breakout"),
            float(strategy=="mean_reversion"),float(regime=="bull"),
            float(regime=="sideways"),float(regime=="bear"),
            min(5.,max(0.,float(row.get("stop_distance",.02))*50)),
            min(5.,max(0.,float(row.get("reward_risk",2))/3)))

def sigmoid(x):
    x=max(-30.,min(30.,x))
    return 1/(1+math.exp(-x))

def fit(trades,min_samples=40,epochs=300,learning_rate=.08,regularization=.08):
    samples=[(vector(t),1. if float(t["pnl"])>0 else 0.) for t in trades
             if t.get("strategy") in ("trend","breakout","mean_reversion")
             and "pnl" in t]
    if len(samples)<min_samples:return None
    weights=[0.]*len(FEATURES)
    for _ in range(epochs):
        gradients=[0.]*len(weights)
        for features,label in samples:
            err=sigmoid(sum(a*b for a,b in zip(weights,features)))-label
            for j,x in enumerate(features):gradients[j]+=err*x
        for j in range(len(weights)):
            penalty=regularization*weights[j] if j else 0.
            weights[j]-=learning_rate*(gradients[j]/len(samples)+penalty)
    return tuple(weights)

def predict(model,row):
    if model is None:return None
    return sigmoid(sum(a*b for a,b in zip(model,vector(row))))

def diagnostics(model,trades):
    if model is None:return {"trained":False,"samples":len(trades)}
    scored=[(predict(model,t),float(t["pnl"])>0) for t in trades if "pnl" in t]
    if not scored:return {"trained":True,"samples":0}
    brier=sum((p-float(y))**2 for p,y in scored)/len(scored)
    return {"trained":True,"samples":len(scored),"brier_in_sample":round(brier,6),
            "coefficients":dict(zip(FEATURES,[round(x,6) for x in model]))}
