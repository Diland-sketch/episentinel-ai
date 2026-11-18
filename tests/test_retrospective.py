"""Prefix-only B06 use, real historical checks, no automatic model execution."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
import pytest
from app import retrospective as ia
from app import retrospective_app as ui
from tests.test_platform_app import artifacts
from tests.test_applied_demo import demo


def request(frame,method="ultimo_valor",cut=779):return ia.prepare(frame,"test-hash","76001",cut,method)


def synthetic():
    return pd.DataFrame([np.arange(832)%17+1],index=["76001"],columns=pd.date_range("2007-01-01",periods=832,freq="7D"))


def test_future_never_enters_worker_and_predictions_are_invariant():
    frame=synthetic(); first=request(frame)
    changed=frame.copy();changed.iloc[0,780:]=-999
    second=request(changed)
    assert first==second and len(first["values"])==780
    assert ia.fit_prefix(first)["points"]==ia.fit_prefix(second)["points"]
    result=ia.fit_prefix(first)
    _,metrics,_=ia.evaluate(first,result,frame.loc["76001"])
    _,other,reasons=ia.evaluate(first,result,changed.loc["76001"])
    assert metrics and not other and reasons


@pytest.mark.parametrize("change",["cut","method","source","series"])
def test_configuration_identity_changes(change):
    f=synthetic();r=request(f)
    if change=="cut":s=request(f,cut=783)
    elif change=="method":s=request(f,method="ingenua_estacional")
    elif change=="source":s=ia.prepare(f,"other-hash","76001",779,"ultimo_valor")
    else:
        f.loc["05001"]=f.loc["76001"]
        s=ia.prepare(f,"test-hash","05001",779,"ultimo_valor")
    assert s["request_id"]!=r["request_id"]


def test_incompatible_dates_are_rejected_without_conversion():
    f=synthetic();dates=list(f.columns);dates[10]+=pd.Timedelta(days=1);f.columns=pd.DatetimeIndex(dates)
    with pytest.raises(ValueError,match="No se corrige"):request(f)
    with pytest.raises(ValueError,match="cuadrícula"):request(synthetic(),cut=778)


def test_zero_scale_and_missing_targets_do_not_create_metrics():
    f=synthetic();f.iloc[0,:780]=4
    r=request(f);result=ia.fit_prefix(r)
    rows,m,reasons=ia.evaluate(r,result,f.loc["76001"])
    assert m["MASE"] is None and reasons and len(rows)==8
    f.iloc[0,781]=np.nan
    rows,m,reasons=ia.evaluate(r,result,f.loc["76001"])
    assert rows[1]["observed"] is None and not m and reasons


def test_b06_rejects_insufficient_or_constant_series_without_partial_curve():
    f=synthetic();r=request(f,method="sarima_sin_estacional")
    r.update(cut=7,values=r["values"][:8],dates=r["dates"][:8])
    result=ia.fit_prefix(r)
    assert result["status"]=="rechazado" and result["points"]==[]
    r=request(f,method="sarima_estacional");r["values"]=[0]*780
    result=ia.fit_prefix(r)
    assert result["error"]["code"]=="SERIE_CONSTANTE_NO_ADMITIDA" and result["points"]==[]


def test_timeout_and_busy_never_produce_partial_results(monkeypatch):
    r=request(synthetic())
    def expired(*args,**kwargs):raise subprocess.TimeoutExpired("worker",1)
    monkeypatch.setattr(ia.subprocess,"run",expired)
    assert ia.execute_bounded(r,timeout=1)["error"]["code"]=="TIMEOUT"
    ia.SLOT.acquire()
    try: assert ia.execute_bounded(r)["error"]["code"]=="BUSY"
    finally:ia.SLOT.release()


def test_ui_requires_click_and_invalidates_on_method_or_cut(artifacts,monkeypatch):
    calls=[]
    def run(r):calls.append(deepcopy(r));return ia.fit_prefix(r)
    monkeypatch.setattr(ui,"execute_bounded",run)
    page=demo();page.radio(key="epi_demo_section").set_value("Pronóstico retrospectivo").run()
    page.selectbox(key="epi_ia_method").select("ultimo_valor").run()
    assert not calls and not page.get("plotly_chart")
    page.button(key="epi_ia_run").click().run()
    assert not page.exception and len(calls)==1 and len(page.get("plotly_chart"))==1
    page.selectbox(key="epi_ia_cut").select(783).run()
    assert not page.exception and len(calls)==1 and not page.get("plotly_chart")
    page.selectbox(key="epi_ia_method").select("ingenua_estacional").run()
    assert len(calls)==1 and not page.metric


def test_nonconvergence_is_visible_without_curve_or_metrics(artifacts,monkeypatch):
    monkeypatch.setattr(ui,"execute_bounded",lambda r:ia.failure(r,"NO_CONVERGENCIA","Optimización no convergente"))
    page=demo();page.radio(key="epi_demo_section").set_value("Pronóstico retrospectivo").run()
    page.button(key="epi_ia_run").click().run()
    assert not page.exception and page.error and not page.get("plotly_chart") and not page.metric
    assert "NO_CONVERGENCIA" in page.error[0].value


@pytest.mark.parametrize("method",ia.B06_METHODS)
def test_real_historical_service_and_saved_evidence(method):
    path=ia.ROOT/"data/processed/panel_casos.parquet"
    if not path.exists():pytest.skip("Local historical panel required")
    frame,digest=ia.load_panel();r=ia.prepare(frame,digest,"76001",779,method)
    result=ia.execute_bounded(r)
    assert result["status"]=="ok", result["error"]
    record=ia.evidence(r,result,frame.loc["76001"])
    saved=json.loads((ia.ROOT/f"docs/experiments/ia_i1_cali_779_{method}.json").read_text())
    np.testing.assert_allclose([p["yhat"] for p in result["points"]],[p["yhat"] for p in saved["forecast"]["points"]],rtol=1e-8)
    assert [row["observed"] for row in record["evaluation"]["rows"]]==[57,66,57,48,68,51,50,58]
    assert len(r["values"])==780 and record["evaluation"]["metrics"]["MAE"]>=0
    if method.startswith("sarima"):
        assert result["diagnostics"]["converged"] is True
        assert result["interval_level"]==.95 and all(p["lo"]<=p["yhat"]<=p["hi"] for p in result["points"])
    else:assert result["interval_level"] is None


def test_interval_plot_keeps_real_bounds_and_never_uses_alert_markers():
    record=json.loads((ia.ROOT/"docs/experiments/ia_i1_cali_779_sarima_sin_estacional.json").read_text())
    chart=ui.figure(record)
    band=next(trace for trace in chart.data if trace.fill=="toself")
    assert band.mode=="lines"
    assert list(band.y)==[r["hi"] for r in record["evaluation"]["rows"]]+[r["lo"] for r in record["evaluation"]["rows"]][::-1]
    assert list(chart.data[-1].y)==[p["yhat"] for p in record["forecast"]["points"]]


def test_evaluation_rejects_forecast_from_another_configuration():
    frame=synthetic();r=request(frame);result=ia.fit_prefix(r)
    changed=request(frame,method="ingenua_estacional")
    with pytest.raises(ValueError,match="configuración distinta"):ia.evidence(changed,result,frame.loc["76001"])
