"""Append-only GitHub training memory for completed CryptoAgent research runs.
Stores immutable run reports under training-memory/v5/runs/<run-id>.json.
Requires GITHUB_TOKEN with contents:write; never stores exchange credentials.
"""
import argparse,base64,datetime,hashlib,json,os,urllib.request,urllib.error
from pathlib import Path

ROOT="training-memory/v5/runs"
def make_record(report,run_id,sha,workflow,source_days):
    if not str(run_id).isdigit():raise ValueError("Invalid GitHub run id")
    raw=json.dumps(report,sort_keys=True,separators=(",",":")).encode()
    return {"schema_version":1,"run_id":str(run_id),"source_commit":sha,
            "workflow":workflow,"history_days":int(source_days),
            "recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "report_sha256":hashlib.sha256(raw).hexdigest(),
            "report":report}

def persist(report_path,run_id,sha,workflow,days,repository,token):
    if not token or not repository:raise ValueError("GitHub repository/token required")
    report=json.loads(Path(report_path).read_text())
    record=make_record(report,run_id,sha,workflow,days)
    path=f"{ROOT}/{run_id}.json"
    url=f"https://api.github.com/repos/{repository}/contents/{path}"
    payload={"message":f"Archive CryptoAgent V5 training run {run_id}",
             "content":base64.b64encode((json.dumps(record,indent=2,sort_keys=True)+"\n").encode()).decode(),
             "branch":"main"}
    request=urllib.request.Request(url,data=json.dumps(payload).encode(),method="PUT",
                headers={"Authorization":f"Bearer {token}",
                         "Accept":"application/vnd.github+json",
                         "X-GitHub-Api-Version":"2022-11-28",
                         "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            result=json.load(response)
    except urllib.error.HTTPError as error:
        if error.code==422:
            raise RuntimeError("Run record already exists; refusing to overwrite") from error
        raise
    return {"path":path,"commit":result["commit"]["sha"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--days",type=int,required=True)
    args=parser.parse_args()
    result=persist(args.report,os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_SHA"],
        os.environ.get("GITHUB_WORKFLOW","CryptoAgent V5"),
        args.days,os.environ["GITHUB_REPOSITORY"],os.environ["GITHUB_TOKEN"])
    print(json.dumps(result))

if __name__=="__main__":main()
