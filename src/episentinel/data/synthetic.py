"""Generador sintético de un panel municipio x semana de casos de dengue.

Propósito (tarea A2 de PAQUETE_EQUIPO_EPISENTINEL.md): dar a las pistas B y C
un panel con la MISMA FORMA que tendrá el panel real (contrato de la sección
2.2 del paquete de equipo), para que puedan empezar a trabajar en líneas base
y modelos sin esperar a que la pista A entregue los datos reales (A6).

Esto es un generador de prueba, no un sustituto del dataset real de SIVIGILA.
Cualquier cifra o conclusión obtenida sobre estos datos sintéticos debe
etiquetarse como tal y no debe citarse en el documento técnico como un
resultado real.

Contrato de salida (ver PAQUETE_EQUIPO_EPISENTINEL.md, sección 2.2 y 9):
    - filas:    cod_mun, texto de 5 dígitos
    - columnas: fechas semanales (pandas.DatetimeIndex)
    - valores:  enteros >= 0
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_panel(
    n_municipios: int = 60,
    start_year: int = 2015,
    end_year: int = 2022,
    seed: int = 42,
    base_rate_range: tuple[float, float] = (2.0, 10.0),
    n_outbreaks: int = 8,
) -> pd.DataFrame:
    """Genera un panel sintético municipio x semana de casos de dengue.

    Imita, a propósito, características que se documentaron en el EDA real
    de la Fase 1 (sobredispersión, estacionalidad anual, ciclos epidémicos
    multianuales y brotes locales), para que una línea base o un modelo que
    funcione aquí tenga sentido probarlo también sobre el panel real.

    Parameters
    ----------
    n_municipios : int
        Número de municipios sintéticos a generar.
    start_year, end_year : int
        Años cubiertos (inclusive). Cada año tiene exactamente 52 semanas
        (igual que el panel real: ver PAQUETE, sección 8, "la malla de 52
        semanas por año altera ligeramente la estacionalidad").
    seed : int
        Semilla para reproducibilidad.
    base_rate_range : tuple[float, float]
        Rango (min, max) del nivel base de casos semanales por municipio,
        antes de aplicar estacionalidad y ciclos epidémicos.
    n_outbreaks : int
        Número de brotes locales inyectados en municipios y semanas
        aleatorias, para poder probar la detección de anomalías.

    Returns
    -------
    pandas.DataFrame
        Filas indexadas por `cod_mun` (string de 5 dígitos), columnas son
        un DatetimeIndex semanal, valores son conteos enteros no negativos.
    """
    if n_municipios < 1:
        raise ValueError("n_municipios debe ser >= 1")
    if end_year < start_year:
        raise ValueError("end_year debe ser >= start_year")

    rng = np.random.default_rng(seed)
    n_years = end_year - start_year + 1
    n_weeks = n_years * 52

    fechas = pd.date_range(f"{start_year}-01-01", periods=n_weeks, freq="7D")
    cod_mun = [f"{(i % 99) + 1:02d}{(i // 99) + 1:03d}" for i in range(n_municipios)]

    t = np.arange(n_weeks)
    semana = (t % 52) + 1
    estacional = 1 + 0.35 * np.sin(2 * np.pi * (semana - 10) / 52)

    # Ciclo epidémico lento y suave (ver nota en el notebook original sobre
    # evitar saltos abruptos entre años, que no son realistas).
    ciclo = np.exp(0.3 * np.sin(2 * np.pi * t / (52 * 3.5) + rng.uniform(0, 2 * np.pi)))

    base = rng.uniform(*base_rate_range, size=n_municipios)
    mu = base[:, None] * estacional[None, :] * ciclo[None, :]

    # Brotes locales inyectados: picos temporales en municipios aleatorios.
    for _ in range(n_outbreaks):
        m = rng.integers(0, n_municipios)
        centro = rng.integers(20, n_weeks - 20)
        ancho = rng.integers(4, 10)
        amplitud = rng.uniform(4, 10)
        ventana = np.exp(-0.5 * ((t - centro) / ancho) ** 2)
        mu[m, :] += amplitud * base[m] * ventana

    # Conteos sobredispersos (binomial negativa), consistente con el índice
    # de dispersión > 1 observado en el EDA real.
    r = 4.0
    p = r / (r + mu)
    casos = rng.negative_binomial(r, p).astype(np.int64)

    panel = pd.DataFrame(casos, index=pd.Index(cod_mun, name="cod_mun"), columns=fechas)
    return panel


def panel_nacional(panel: pd.DataFrame) -> pd.Series:
    """Serie agregada nacional (suma de todos los municipios por semana)."""
    return panel.sum(axis=0).rename("nacional")
