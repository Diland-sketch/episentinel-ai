"""Explicit bounded historical experiment. No writes except a requested new evidence file."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from app.retrospective import load_panel,prepare,fit_prefix,execute_bounded,evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--series",default="76001")
    parser.add_argument("--cut",type=int,default=779)
    parser.add_argument("--method",default="sarima_sin_estacional")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.worker:
        print(json.dumps(fit_prefix(json.load(sys.stdin)),allow_nan=False));return
    if args.output and (args.output.exists() or ROOT/"docs"/"experiments" not in args.output.resolve().parents):
        parser.error("Output must be a new file inside docs/experiments; existing files are never overwritten")
    frame,digest=load_panel()
    request=prepare(frame,digest,args.series,args.cut,args.method)
    result=evidence(request,execute_bounded(request),frame.loc[args.series])
    content=json.dumps(result,ensure_ascii=True,allow_nan=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as handle:handle.write(content+"\n")
    print(json.dumps({"status":result["forecast"]["status"],"error":result["forecast"]["error"],
        "metrics":result["evaluation"]["metrics"],"diagnostics":result["forecast"]["diagnostics"],"points":result["evaluation"]["rows"]},indent=2))
    if result["forecast"]["status"]!="ok":raise SystemExit(1)


if __name__=="__main__":main()
