"""Canonical manual input, atomic collections, identity and honest partition status."""
from copy import deepcopy
from pathlib import Path
import pytest
from app.session_input import (new_inputs,change_mode,change_csv,add_manual,combine,clear_active,counters,
    provenance,partition_context,encode_rows,MANUAL_MODE,CSV_MODE)
from app.analysis_presenter import new_state,read_profiles,make_config,set_selection,execute
from episentinel.data.csv_loader import load_csv

ROOT=Path(__file__).resolve().parents[1]
CSV=b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,210,0\n76001,2020,53,220,2\n"


def row(**changes):
    return dict(dict(cod_mun="76001",ano="2020",semana="52",cod_eve=210,conteo="0"),**changes)


def manual():
    inputs,work=new_inputs(),new_state()
    change_mode(inputs,work,MANUAL_MODE)
    return inputs,work


def analyze(work):
    profile=read_profiles(ROOT/"configs/ui_period_grids.json")[0]
    for field,value in (("municipality","76001"),("event",210),("profile",profile["id"])):
        set_selection(work,field,value)
    return execute(work,make_config("76001",210,profile))


def test_multiple_records_zero_absence_provenance_and_partition_block():
    i,w=manual()
    assert counters(i,w)["total"]==0
    assert add_manual(i,w,row())
    first=w["source_key"]
    assert add_manual(i,w,row(semana="53",conteo="4"))
    assert counters(i,w)==dict(csv=0,manual=2,valid=2,rejected=0,pending=0,total=2,rejected_attempts=0)
    assert w["source_key"]!=first
    result=analyze(w)
    assert [p.observed_count for p in result.series.series[0].points]==[0,4,None]
    context=partition_context(i,w)
    assert context["eligible_positions"] is None and context["partitions"] is None
    assert context["series"][0]["Observadas"]==2
    assert all(r["Partición"].startswith("Sin asignación") for r in context["rows"])
    assert any("17 posiciones" in reason for reason in context["reasons"])
    assert [r["Registro original"] for r in provenance(i)]==[1,2]
    assert all(r["Origen"]=="Manual declarado" for r in provenance(i))


@pytest.mark.parametrize("changes",[{"cod_mun":""},{"cod_mun":"7600"},{"cod_mun":"01001"},{"cod_mun":"76000"},
    {"ano":"2020.0"},{"ano":"20"},{"semana":"54"},{"semana":"-1"},{"cod_eve":999},{"cod_eve":None},
    {"conteo":""},{"conteo":"-1"},{"conteo":"1,000"},{"conteo":"0.5"}])
def test_invalid_manual_matches_csv_validation_exactly(changes):
    i,w=manual();raw=row(**changes)
    direct=load_csv(encode_rows([raw]),source_name="equivalence.csv")
    assert direct.blocked and not add_manual(i,w,raw)
    report=i["feedback"]["report"]
    assert [(e["code"],e["column"],e["record"]) for e in report["errors"]]==[(e["code"],e["column"],e["record"]) for e in direct.report["errors"]]
    assert counters(i,w)["total"]==0 and counters(i,w)["rejected_attempts"]==1
    assert w["result"] is None and w["payload"] is None


@pytest.mark.parametrize("count",["0","3"])
def test_duplicate_and_conflict_reject_only_attempt_without_mutating_active_data(count):
    i,w=manual();assert add_manual(i,w,row())
    analyze(w);before=deepcopy(w);version=i["version"]
    assert not add_manual(i,w,row(conteo=count))
    assert w==before and i["version"]==version
    assert counters(i,w)["valid"]==1 and counters(i,w)["rejected_attempts"]==1
    assert any(e["code"]=="duplicate" for e in i["feedback"]["report"]["errors"])


def test_same_period_different_event_is_not_a_duplicate_or_new_week():
    i,w=manual();add_manual(i,w,row());assert add_manual(i,w,row(cod_eve=220,conteo="2"))
    assert counters(i,w)["total"]==2
    assert len({(r["ano"],r["semana"]) for r in w["load"].data})==1


def test_csv_counts_are_atomic_and_pending_rows_not_called_valid():
    i,w=new_inputs(),new_state()
    change_csv(i,w,CSV+b"76001,2021,1,210,-1\n","invalid.csv")
    assert counters(i,w)==dict(csv=3,manual=0,valid=0,rejected=1,pending=2,total=3,rejected_attempts=0)


def test_explicit_combination_revalidates_cross_source_keys_and_source_switches():
    i,w=new_inputs(),new_state();change_csv(i,w,CSV,"test.csv")
    assert counters(i,w)["total"]==2
    change_mode(i,w,MANUAL_MODE)
    assert counters(i,w)["total"]==0
    assert combine(i,w,True)
    assert not add_manual(i,w,row())  # duplicate against CSV, no silent sum
    assert counters(i,w)["total"]==2
    assert add_manual(i,w,row(cod_mun="05001",cod_eve=580,conteo="1"))
    assert (counters(i,w)["csv"],counters(i,w)["manual"],counters(i,w)["total"])==(2,1,3)
    assert [r["Origen"] for r in provenance(i)]==["CSV","CSV","Manual declarado"]
    change_mode(i,w,CSV_MODE)
    assert counters(i,w)["total"]==2 and counters(i,w)["manual"]==0
    clear_active(i,w)
    change_mode(i,w,MANUAL_MODE)
    assert counters(i,w)["total"]==1 and not i["include_csv"]


def test_failed_combination_preserves_manual_set_and_old_csv_bytes():
    i,w=new_inputs(),new_state();change_csv(i,w,CSV,"test.csv")
    change_mode(i,w,MANUAL_MODE);add_manual(i,w,row(conteo="20"))
    before=deepcopy(w)
    assert not combine(i,w,True)
    assert w==before and not i["include_csv"] and i["csv_payload"]==CSV


def test_successful_addition_and_source_change_invalidate_results():
    i,w=manual();add_manual(i,w,row());analyze(w)
    assert add_manual(i,w,row(semana="53",conteo="4"))
    assert w["result"] is None and w["execution_key"] is None
    change_mode(i,w,CSV_MODE)
    assert w["payload"] is None and not w["result"]


def test_sessions_are_independent_and_adapter_never_writes_files(monkeypatch):
    def forbidden(*a,**k):pytest.fail("Manual entry attempted a filesystem write")
    monkeypatch.setattr(Path,"write_bytes",forbidden);monkeypatch.setattr(Path,"write_text",forbidden)
    i,w=manual();other,other_work=manual()
    assert add_manual(i,w,row())
    assert i["session_id"]!=other["session_id"]
    assert counters(other,other_work)["total"]==0 and other_work["result"] is None
