"""Causal archived-model warm start. Never import a model trained after fold cutoff."""
import hashlib,json
from pathlib import Path
from learner_v4 import FEATURES

def previous_weights(cutoff,root="training-memory/v5/runs"):
    best={}
    for path in Path(root).glob("*.json"):
        try:
            record=json.loads(path.read_text())
            report=record["report"]
            raw=json.dumps(report,sort_keys=True,separators=(",",":")).encode()
            if hashlib.sha256(raw).hexdigest()!=record.get("report_sha256"):
                continue
            for fold in report.get("folds",[]):
                # Calibration and training of the old snapshot must both precede new training.
                completed=fold.get("cal_end")
                if not completed or completed>=cutoff:continue
                for name,snapshot in fold.get("model_snapshots",{}).items():
                    weights=snapshot.get("weights",[])
                    if len(weights)!=len(FEATURES):continue
                    if any(not isinstance(w,(float,int)) for w in weights):continue
                    if name not in best or completed>best[name][0]:
                        best[name]=(completed,tuple(weights),record.get("run_id"))
        except (ValueError,KeyError,TypeError,OSError):
            continue
    return {name:{"cutoff":date,"weights":weights,"source_run":run_id}
            for name,(date,weights,run_id) in best.items()}
