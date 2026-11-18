"""Bounded, explicit synthetic B04/B05/B03 benchmark. Never trains models.

python -B scripts/benchmark_demo.py --output docs/benchmarks/science_demo_i1.json
Stages are timed in an isolated worker using transparent timing wrappers only.
Original functions receive unchanged arguments and return unchanged results.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
MAX_ROWS=100_000
MAX_BYTES=8*1024*1024
MAX_TOTAL_SECONDS=120


def validate_sizes(sizes,repetitions):
    if not 1 <= len(sizes) <= 4 or any(type(n) is not int or not 1<=n<=MAX_ROWS for n in sizes):
        raise ValueError("Use entre 1 y 4 tamaños de 1 a 100000 filas")
    if type(repetitions) is not int or not 1<=repetitions<=3:
        raise ValueError("Repeticiones permitidas: 1 a 3")


def synthetic_csv(rows):
    validate_sizes([rows],1)
    lines=["cod_mun,ano,semana,cod_eve,conteo"]
    for i in range(rows):
        group,pos=divmod(i,832)
        lines.append(f"{50001+group:05d},{2007+pos//52},{pos%52+1},210,{i%29}")
    payload=("\n".join(lines)+"\n").encode("ascii")
    if len(payload)>MAX_BYTES: raise ValueError("CSV exceeds 8 MiB safety bound")
    return payload


def worker(rows):
    from episentinel.data import csv_contract
    from episentinel.data.epidemiological_series import CalendarMetadata, MunicipalIdentity, PeriodGrid
    from episentinel.services import isolated_pipeline as pipeline
    validate_sizes([rows],1)
    tracemalloc.start()
    try:
        payload=synthetic_csv(rows)
        grid=PeriodGrid(tuple((2007+i//52,i%52+1) for i in range(832)),
            CalendarMetadata("synthetic-52-grid","1","Artificial positional fixture; not official calendar"))
        config=pipeline.PipelineConfig("synthetic-benchmark-v1",MunicipalIdentity("50001"),(210,),grid)
        durations={"ingestion_s":0.,"load_s":0.,"construction_s":0.}
        def timed(function,key):
            def call(*args,**kwargs):
                start=time.perf_counter()
                try: return function(*args,**kwargs)
                finally: durations[key]+=time.perf_counter()-start
            return call
        with patch.object(csv_contract,"read_csv_records",timed(csv_contract.read_csv_records,"ingestion_s")), \
             patch.object(pipeline,"load_csv",timed(pipeline.load_csv,"load_s")), \
             patch.object(pipeline,"build_series",timed(pipeline.build_series,"construction_s")):
            start=time.perf_counter()
            result=pipeline.run_pipeline(payload,config=config,source_name="ARTIFICIAL.csv")
            elapsed=time.perf_counter()-start
        _,peak=tracemalloc.get_traced_memory()
        series=result.series.series[0] if result.series else None
        return {"rows":rows,"csv_bytes":len(payload),"csv_sha256":hashlib.sha256(payload).hexdigest(),
                "municipal_candidates":(rows+831)//832,"selected_series":"50001/210",
                "status":result.status,"pipeline_s":elapsed,"ingestion_s":durations["ingestion_s"],
                "validation_s":durations["load_s"]-durations["ingestion_s"],
                "construction_s":durations["construction_s"],"b04_total_s":durations["load_s"],
                "python_peak_mib":peak/(1024*1024),"rss_peak_mib":None,
                "observed_selected":series.coverage.observed_periods if series else None,
                "expected_selected":832,"errors":[asdict(e) for e in result.errors],"warnings":len(result.warnings)}
    finally:
        tracemalloc.stop()


def environment():
    paths=("scripts/benchmark_demo.py","src/episentinel/data/csv_contract.py",
           "src/episentinel/data/csv_loader.py","src/episentinel/data/epidemiological_series.py",
           "src/episentinel/services/isolated_pipeline.py")
    return {"python":platform.python_version(),"platform":platform.platform(),"processor":platform.processor(),
            "episentinel":importlib.metadata.version("episentinel-ai"),
            "code_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}


def run_benchmark(sizes=(1000,10000,50000),repetitions=1,timeout=30):
    validate_sizes(sizes,repetitions)
    if not 1<=timeout<=45: raise ValueError("Tiempo máximo por proceso: 1 a 45 segundos")
    results=[]
    start=time.monotonic()
    for size in sizes:
        for repeat in range(1,repetitions+1):
            remaining=MAX_TOTAL_SECONDS-(time.monotonic()-start)
            row={"rows":size,"repeat":repeat}
            if remaining<=0:
                row.update(status="budget_skipped",errors=["Total benchmark time budget exhausted"])
            else:
                try:
                    process=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),"--worker",str(size)],
                        capture_output=True,text=True,encoding="utf-8",timeout=min(timeout,remaining),
                        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    if process.returncode:
                        row.update(status="failed",errors=[process.stderr[-2000:] or f"exit {process.returncode}"])
                    else:
                        row.update(json.loads(process.stdout))
                except subprocess.TimeoutExpired:
                    row.update(status="timeout",errors=["Worker terminated at wall-clock limit"])
                except (ValueError,OSError) as exc:
                    row.update(status="failed",errors=[f"{type(exc).__name__}: {exc}"])
            results.append(row)
    return {"schema":"episentinel-synthetic-benchmark-v1","synthetic":True,
            "created_utc":datetime.now(timezone.utc).isoformat(),"environment":environment(),
            "limits":{"max_rows":MAX_ROWS,"max_csv_bytes":MAX_BYTES,"worker_timeout_s":timeout,
                      "total_budget_s":MAX_TOTAL_SECONDS,"memory_hard_limit":None},
            "methodology":{"dataset":"Deterministic artificial municipal codes, 832 technical positions, event 210, count=i%29; zeros included. No real observations.",
                "timing":"B05 end-to-end with wrappers forwarding unchanged calls. CSV syntax/hash/read inside B04; validation_s=B04 total minus ingestion; construction_s=build_series. Orchestration/deepcopy overhead remains in B05 total.",
                "memory":"tracemalloc Python allocations including synthetic generation, grid and pipeline; excludes interpreter startup and native/RSS allocations. Instrumented times, not uninstrumented throughput.",
                "scope":"B03 validates all delivered rows and builds only explicitly selected 50001/210; not all municipalities. No file I/O timing (payload in memory), no model calls or network, no extrapolation."},
            "results":results}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes",nargs="+",type=int,default=[1000,10000,50000])
    parser.add_argument("--repetitions",type=int,default=1)
    parser.add_argument("--timeout",type=int,default=30)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--worker",type=int,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker is not None:
        try: report=worker(args.worker)
        except Exception as exc: report={"rows":args.worker,"status":"failed","errors":[f"{type(exc).__name__}: {exc}"]}
        print(json.dumps(report,ensure_ascii=True))
        return
    if args.output:
        target=args.output.resolve()
        if target.exists(): parser.error("Output already exists; refusing to overwrite")
        if target.suffix!=".json": parser.error("Output must be a new JSON summary")
        if ROOT in target.parents and ROOT/"docs"/"benchmarks" not in target.parents:
            parser.error("Inside repository only docs/benchmarks may receive a new summary")
    report=run_benchmark(args.sizes,args.repetitions,args.timeout)
    text=json.dumps(report,ensure_ascii=True,indent=2)
    if args.output:
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("x",encoding="utf-8") as handle: handle.write(text+"\n")
    print(text)
    if any(row["status"]!="completed" for row in report["results"]): raise SystemExit(1)


if __name__=="__main__": main()
