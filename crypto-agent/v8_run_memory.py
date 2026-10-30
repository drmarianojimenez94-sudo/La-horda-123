"""V8 run memory: immutable versioned research summaries, causal comparisons.
Past validation metrics may guide candidate prioritization, never replace new validation.
"""
import json,hashlib
from pathlib import Path
from event_memory_v7 import EventMemory

def store_run(report,db_path,run_id,trained_until_ms):
    m=EventMemory(db_path)
    try:
        fingerprint=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
        existing=[x for x in m.models() if x["version"]==str(run_id)]
        if existing:
            if existing[0]["parameters"]["sha256"]!=fingerprint:
                raise ValueError("Conflicting immutable run")
            return fingerprint
        m.save_model(str(run_id),trained_until_ms,{"sha256":fingerprint,
            "selected":report.get("selected")},{"ranked": [
            {"id":x["id"],"validation_mean_pct":x["validation_mean_pct"]}
            for x in report.get("ranked",[])[:10]]})
        return fingerprint
    finally:m.close()

def prior_candidates(db_path,training_cutoff_ms):
    if not Path(db_path).exists():return []
    m=EventMemory(db_path)
    try:
        return [{"run":x["version"],"trained_until_ms":x["trained_until_ms"],"selected":x["parameters"].get("selected"),
                 "validation_top":x["metrics"].get("ranked",[])}
                for x in m.models() if x["trained_until_ms"]<training_cutoff_ms]
    finally:m.close()
