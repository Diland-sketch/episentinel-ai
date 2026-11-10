"""Metricas de pronostico para comparar baseline vs modelo propuesto (B5/C4)."""
from __future__ import annotations
import numpy as np


def mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))))


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)) ** 2)))


def mase(y_true, y_pred, y_train, m: int = 52) -> float:
    y_train = np.asarray(y_train, dtype=float)
    if len(y_train) <= m:
        return float("nan")
    denom = np.mean(np.abs(y_train[m:] - y_train[:-m]))
    if not denom:
        return float("nan")
    return float(mae(y_true, y_pred) / denom)


def cobertura_intervalo(y_true, lo, hi) -> float:
    y_true = np.asarray(y_true, dtype=float)
    return float(np.mean((y_true >= np.asarray(lo)) & (y_true <= np.asarray(hi))))