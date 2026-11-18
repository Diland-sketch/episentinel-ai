"""Bounded benchmark harness; synthetic fixtures, no scientific model execution."""
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
from scripts import benchmark_demo as bench
from episentinel.data.csv_loader import load_csv


@pytest.mark.parametrize("rows",[1,833,1000])
def test_generator_is_deterministic_canonical_unique_and_bounded(rows):
    one=bench.synthetic_csv(rows)
    assert one==bench.synthetic_csv(rows) and len(one)<bench.MAX_BYTES
    result=load_csv(one,source_name="ARTIFICIAL.csv")
    assert not result.blocked and len(result.data)==rows
    assert result.data[0]["conteo"]==0
    assert len({(r["cod_mun"],r["ano"],r["semana"],r["cod_eve"]) for r in result.data})==rows


@pytest.mark.parametrize("sizes,repetitions",[([0],1),([100001],1),([True],1),([1]*5,1),([1],4),([1],False)])
def test_resource_limits_reject_before_generation(sizes,repetitions):
    with pytest.raises(ValueError): bench.validate_sizes(sizes,repetitions)


def test_actual_worker_records_stages_and_restores_instrumentation():
    from episentinel.data import csv_contract
    from episentinel.services import isolated_pipeline
    functions=(csv_contract.read_csv_records,isolated_pipeline.load_csv,isolated_pipeline.build_series)
    result=bench.worker(1000)
    assert result["status"]=="completed" and result["errors"]==[]
    assert result["observed_selected"]==832
    assert 0<=result["ingestion_s"]<=result["b04_total_s"]<=result["pipeline_s"]
    assert result["validation_s"]+result["ingestion_s"]==pytest.approx(result["b04_total_s"])
    assert result["pipeline_s"]>=result["b04_total_s"]+result["construction_s"]
    assert result["python_peak_mib"]>0 and result["rss_peak_mib"] is None
    assert functions==(csv_contract.read_csv_records,isolated_pipeline.load_csv,isolated_pipeline.build_series)


def test_timeouts_and_worker_failures_are_recorded_without_fake_measurements(monkeypatch):
    def expired(*args,**kwargs): raise subprocess.TimeoutExpired("synthetic",1)
    monkeypatch.setattr(bench.subprocess,"run",expired)
    record=bench.run_benchmark([10],timeout=1)["results"][0]
    assert record["status"]=="timeout" and record["errors"]
    assert "pipeline_s" not in record
    monkeypatch.setattr(bench.subprocess,"run",lambda *a,**k:SimpleNamespace(returncode=1,stderr="controlled failure"))
    record=bench.run_benchmark([10])["results"][0]
    assert record["status"]=="failed" and record["errors"]==["controlled failure"]


def test_existing_summary_is_never_overwritten(tmp_path,monkeypatch):
    target=tmp_path/"existing.json"
    target.write_text("keep")
    monkeypatch.setattr(bench.sys,"argv",["benchmark_demo.py","--output",str(target)])
    with pytest.raises(SystemExit): bench.main()
    assert target.read_text()=="keep"
