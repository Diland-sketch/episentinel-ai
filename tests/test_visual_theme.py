"""Presentation regression: no change to plotted data or temporal gaps."""
from copy import deepcopy
from html import unescape

import numpy as np
import plotly.graph_objects as go
import pytest

from app.analysis_presenter import execute, make_config, new_state, observed_figure, read_profiles, set_source
from app.visual_theme import heatmap_labels, style_figure
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("count", [2, 20, 40])
def test_full_territory_labels_and_hover_counts_survive_layout(count):
    labels = [f"San José de un territorio largo {i} (76001)" for i in range(count)]
    counts = np.arange(count * 3).reshape(count, 3)
    fig = go.Figure(go.Heatmap(x=[2020, 2021, 2022], y=labels,
        z=np.log1p(counts), customdata=counts, colorscale="Greens",
        hovertemplate="%{y}: %{customdata} casos<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    before = fig.to_dict()["data"]
    heatmap_labels(style_figure(fig))
    assert fig.to_dict()["data"][0]["z"] == before[0]["z"]
    assert fig.to_dict()["data"][0]["customdata"] == before[0]["customdata"]
    assert list(fig.data[0].y) == labels
    assert list(fig.layout.yaxis.tickvals) == labels  # no auto-skipping territories
    assert [unescape(text.replace("<br>", " ")) for text in fig.layout.yaxis.ticktext] == labels
    assert fig.layout.yaxis.autorange == "reversed"
    assert fig.data[0].hovertemplate == before[0]["hovertemplate"]
    assert fig.to_dict()["data"][0]["colorscale"] == before[0]["colorscale"]
    assert fig.layout.margin.l >= 130
    assert fig.layout.height >= count * 36


def test_theme_preserves_all_forecast_interval_and_observation_traces():
    fig = go.Figure([
        go.Scatter(x=[1, 2], y=[2, 3], name="Observado", connectgaps=False),
        go.Scatter(x=[1, 2, 2, 1], y=[4, 5, 1, 0], fill="toself", name="Intervalo"),
        go.Scatter(x=[1, 2], y=[2.5, 3.5], name="Pronóstico"),
    ])
    fig.add_vrect(x0=1, x1=2)
    before = deepcopy(fig.to_dict())
    style_figure(fig)
    assert fig.to_dict()["data"] == before["data"]
    assert fig.to_dict()["layout"]["shapes"] == before["layout"]["shapes"]


def test_compact_chart_keeps_observed_zero_and_middle_gap_separate():
    state = new_state()
    set_source(state, b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,210,0\n76001,2021,1,210,4\n", "synthetic-test.csv")
    profile = read_profiles(ROOT / "configs/ui_period_grids.json")[0]
    result = execute(state, make_config("76001", 210, profile))
    before = deepcopy(result)
    fig = observed_figure(result.series.series[0])
    assert list(fig.data[0].y) == [0, None, 4]
    assert fig.data[0].connectgaps is False
    assert list(fig.data[1].x) == ["2020 · S53"]
    assert fig.data[1].yaxis == "y2" and list(fig.data[1].y) == [.5]
    assert fig.layout.height <= 340
    assert result == before
