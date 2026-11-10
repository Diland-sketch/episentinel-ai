"""Tarea B5/C4: evaluacion comparativa sobre datos reales.

Entrena con 2007-2021 (indices 0-779) y pronostica las 52 semanas de 2022
(indices 780-831, conjunto de prueba segun configs/split.json).

Modelos: ingenua estacional, ingenua de ultimo valor, SARIMA estacional
(1,1,1)(1,0,1)[52] y SARIMA sin estacional (1,1,1). Series: nacional + los
5 municipios con mas casos (NO las 65 de series_seleccionadas.csv).
Escribe reports/comparacion_fase2.csv y .json.
"""
import json
import time

import pandas as pd

from episentinel.baselines.ingenua_estacional import (
    pronosticar_ingenua_estacional, pronosticar_ultimo_valor,
)
from episentinel.evaluation.forecast_metrics import cobertura_intervalo, mae, mase, rmse
from episentinel.models.sarima import ajustar_sarima, pronosticar

VAL_END = 779
TEST_END = 831
N_MUNICIPIOS_EVAL = 5

panel = pd.read_parquet("data/processed/panel_casos.parquet")
panel.columns = pd.to_datetime(panel.columns)
nacional = panel.sum(axis=0)
top_mun = panel.sum(axis=1).sort_values(ascending=False).index[:N_MUNICIPIOS_EVAL]

series = {"NACIONAL": nacional}
series.update({str(c): panel.loc[c] for c in top_mun})

filas = []
for nombre, serie in series.items():
    train = serie.iloc[: VAL_END + 1]
    test = serie.iloc[VAL_END + 1 : TEST_END + 1]
    pasos = len(test)
    y_true = test.values

    def fila(modelo, yhat, lo=None, hi=None, seg=0.0):
        f = {"serie": nombre, "modelo": modelo, "mae": mae(y_true, yhat), "rmse": rmse(y_true, yhat),
             "mase": mase(y_true, yhat, train.values), "tiempo_s": round(seg, 3)}
        if lo is not None:
            f["cobertura_ic95"] = cobertura_intervalo(y_true, lo, hi)
        filas.append(f)

    fila("ingenua_estacional", pronosticar_ingenua_estacional(train, pasos).values)
    fila("ingenua_ultimo_valor", pronosticar_ultimo_valor(train, pasos).values)

    for modelo, sorder in [("sarima_estacional", (1, 0, 1, 52)), ("sarima_sin_estacional", (0, 0, 0, 0))]:
        t0 = time.perf_counter()
        res = ajustar_sarima(train.astype(float), order=(1, 1, 1), seasonal_order=sorder)
        p = pronosticar(res, pasos=pasos, fechas=test.index)
        fila(modelo, p["yhat"].values, p["lo"].values, p["hi"].values, time.perf_counter() - t0)

df = pd.DataFrame(filas)
df.to_csv("reports/comparacion_fase2.csv", index=False)
with open("reports/comparacion_fase2.json", "w", encoding="utf-8") as f:
    json.dump(filas, f, indent=2, ensure_ascii=False)

print(df.round(3).to_string(index=False))
print("\nMASE promedio por modelo (menor es mejor):")
print(df.groupby("modelo")["mase"].mean().round(3))