"""Offline V7 memory analysis: matured rejected and accepted shadow opportunities.
Never uses test labels to train or calibrate; writes a versioned candidate.
"""
import argparse,json
from pathlib import Path
from event_memory_v7 import EventMemory
from event_learning_v7 import build_shadow_labels,purged_time_split,drift_summary
from calibration_v7 import recalibrate_candidate,calibration_report
from benchmarks_v7 import compare

def audit(path,train_end_ms,cal_end_ms,test_end_ms):
    memory=EventMemory(path)
    try:
        # Complete archive, not just latest 100 events.
        records=[dict(timestamp_ms=t,kind=k,symbol=s,payload=json.loads(p))
                 for t,k,s,p in memory.db.execute(
                 "SELECT observed_ms,kind,symbol,payload FROM events ORDER BY id")]
        samples=build_shadow_labels(records)
        train,cal,test=purged_time_split(samples,train_end_ms,cal_end_ms,test_end_ms)
        candidate=recalibrate_candidate(train,cal)
        # Independent test is reporting only; never used for promotion or threshold selection.
        test_report=calibration_report(candidate["model"],test)
        report={"samples":{"train":len(train),"calibration":len(cal),"test":len(test)},
                "calibration":candidate["validation"],"test":test_report,
                "candidate_status":candidate["reason"],
                "benchmarks":{"calibration":compare(cal),"test":compare(test)},
                "training_drift":drift_summary(train),
                "model_promoted":False}
        if candidate["model"] is not None:
            version=f"event-v7-{train_end_ms}-{cal_end_ms}"
            try:
                memory.save_model(version,train_end_ms,candidate["model"],report)
            except __import__("sqlite3").IntegrityError:
                pass # Immutable candidate version already recorded.
        return report
    finally:memory.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",required=True)
    parser.add_argument("--train-end-ms",type=int,required=True)
    parser.add_argument("--cal-end-ms",type=int,required=True)
    parser.add_argument("--test-end-ms",type=int,required=True)
    args=parser.parse_args()
    report=audit(args.db,args.train_end_ms,args.cal_end_ms,args.test_end_ms)
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
