"""Applied demonstration preserves B10 and uses saved artifacts only."""
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from app.experimental_presenter import percentage_protocol, partition_rows, origin_rows, rolling_figure
from episentinel.evaluation.temporal_protocol import TemporalProtocol
from episentinel.evaluation.rolling_origin import plan_rolling_origin
from tests.test_platform_app import artifacts, prohibit_models
from tests.test_lab_app import journey

ROOT=Path(__file__).resolve().parents[1]


def demo():
    page=journey()
    page.radio(key="epi_lab_mode_widget").set_value("Demostración aplicada").run()
    assert not page.exception
    return page


def test_percentage_rounding_has_no_lost_positions_or_boundary_crossing():
    p=percentage_protocol(832,80,10)
    assert (p.train_size,p.validation_end,p.total_size)==(665,748,832)
    assert sum(r["Posiciones"] for r in partition_rows(p))==832
    for o in plan_rolling_origin(p).origins:
        start,end=(p.train_size,p.validation_end) if o.partition=="validation" else (p.validation_end,p.total_size)
        assert len(o.target_positions)==8 and start<=o.target_start<o.target_end<=end
        assert o.cut<o.target_start and o.train_start==0


@pytest.mark.parametrize("args",[(832,90,10),(832,0,10),(12,80,10),(832,True,10),(832,80.1,10),(-1,80,10)])
def test_invalid_percentage_protocol_is_rejected(args):
    with pytest.raises(ValueError): percentage_protocol(*args)


def test_integer_plan_is_exact_b10_example_with_exclusions():
    p=TemporalProtocol(728,780,832)
    plan=plan_rolling_origin(p)
    assert len(plan.origins)==24
    assert [o.cut for o in plan.excluded]==[775,827]
    assert {o.reason for o in plan.excluded}=={"incomplete_partition_horizon"}
    assert len(origin_rows(plan))==24
    fig=rolling_figure(plan,"validation")
    assert len(fig.data)==13 and fig.data[-1].name=="Horizonte incompleto"


def test_saved_metrics_select_series_without_forecasts_or_fitting(artifacts,monkeypatch):
    prohibit_models(monkeypatch)
    page=demo()
    assert len(page.get("plotly_chart"))==1
    page.selectbox(key="epi_demo_series").select("76001").run()
    page.selectbox(key="epi_demo_metric").select("rmse").run()
    assert not page.exception
    assert any("No hay predicciones por periodo" in w.value for w in page.warning)
    assert len(page.dataframe[0].value)==4
    assert set(page.dataframe[0].value["rmse"])=={3.}
    assert not page.button  # no model execution button in this component


def test_planner_invalid_and_recovered_configuration_has_no_metrics_or_models(artifacts,monkeypatch):
    prohibit_models(monkeypatch)
    page=demo()
    page.radio(key="epi_demo_section").set_value("Diseño temporal").run()
    assert not page.exception and len(page.get("plotly_chart"))==2
    page.number_input(key="epi_demo_train_pct").set_value(98).run()
    assert page.error and not page.get("plotly_chart")
    page.radio(key="epi_demo_partition_mode").set_value("Límites enteros").run()
    assert not page.exception and len(page.get("plotly_chart"))==2
    assert [m.value for m in page.metric]==["12","12","2"]
    page.number_input(key="epi_demo_train_end").set_value(790).run()
    assert page.error and not page.get("plotly_chart")
    page.number_input(key="epi_demo_train_end").set_value(728).run()
    page.radio(key="epi_demo_windows").set_value("test").run()
    assert not page.exception
    assert all("MAE" not in m.label for m in page.metric)


def test_missing_comparison_or_benchmark_does_not_invent_results(artifacts):
    (artifacts/"reports/comparacion_fase2.csv").unlink()
    page=demo()
    assert page.warning and not page.get("plotly_chart")
    page.radio(key="epi_demo_section").set_value("Escalabilidad").run()
    assert not page.exception and page.warning and not page.get("plotly_chart")


def test_benchmark_view_is_read_only_with_recorded_results(artifacts):
    target=artifacts/"docs/benchmarks"
    target.mkdir(parents=True)
    record=json.loads((ROOT/"docs/benchmarks/science_demo_i1.json").read_text())
    (target/"science_demo_i1.json").write_text(json.dumps(record))
    page=demo()
    page.radio(key="epi_demo_section").set_value("Escalabilidad").run()
    assert not page.exception and len(page.dataframe[0].value)==3
    assert len(page.get("plotly_chart"))==1
    assert all(page.dataframe[0].value["Estado"]=="completed")


def test_applied_plan_and_observatory_result_survive_environment_changes(artifacts,monkeypatch):
    from app.analysis_presenter import new_state,set_source,set_selection,read_profiles,make_config,execute
    prohibit_models(monkeypatch)
    page=demo()
    state=new_state()
    set_source(state,b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,210,0\n","synthetic.csv")
    profile=read_profiles(ROOT/"configs/ui_period_grids.json")[0]
    for field,value in (("municipality","76001"),("event",210),("profile",profile["id"])):
        set_selection(state,field,value)
    execute(state,make_config("76001",210,profile))
    page.session_state.epi_work=state
    identity=state["execution_key"]
    page.radio(key="epi_demo_section").set_value("Diseño temporal").run()
    page.number_input(key="epi_demo_train_pct").set_value(70).run()
    page.radio(key="epi_platform_nav").set_value("Observatorio Epidemiológico").run()
    assert page.session_state.epi_work["execution_key"]==identity
    page.radio(key="epi_platform_nav").set_value("Laboratorio de Machine Learning").run()
    assert not page.exception
    assert page.radio(key="epi_demo_section").value=="Diseño temporal"
    assert page.number_input(key="epi_demo_train_pct").value==70
    assert page.session_state.epi_work["execution_key"]==identity
