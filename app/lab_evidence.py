"""Read-only evidence catalogue for the twelve phases. No scientific execution."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Phase:
    number: int
    chapter: int
    title: str
    objective: str
    methodology: str
    result: str
    limitations: str
    pending: str
    sources: tuple[str, ...]
    reproduce: str
    view: str | None = None


CHAPTERS = {
    1: ("Problema y datos", "Del propósito epidemiológico a una serie con procedencia."),
    2: ("Diseño experimental", "Cómo representar el pasado y reservar el futuro."),
    3: ("Entrenamiento y evaluación", "Qué se ajustó, qué se midió y qué falta probar."),
    4: ("Generalización y despliegue", "Hasta dónde llega la evidencia y cómo se utiliza."),
}

PHASES = (
    Phase(1, 1, "Definir el problema",
          "Estimar conteos semanales de dengue por municipio y explorar semanas que merecen revisión.",
          "Unidad municipio × semana. Pronóstico de conteos separado de señales de anomalía; mortalidad no equivale a casos.",
          "El proyecto implementa pronósticos y reglas históricas. Una señal no confirma un brote ni mide riesgo por habitante.",
          "La definición operativa de brote y de difícil acceso sigue abierta; no existe un criterio de éxito predictivo ratificado para todo el alcance.",
          "Cerrar población objetivo, horizonte de uso y criterios verificables de éxito; documentar etiquetas si se evalúan señales.",
          ("README.md", "docs/DECISIONES_TECNICAS.md", "docs/ESTADO_DEL_PROYECTO.md"),
          "Contrastar unidad, evento y decisiones abiertas en los documentos; no ejecutar modelos para esta fase."),
    Phase(2, 1, "Recolección de datos",
          "Conservar los tres originales de referencia y comprobar su identidad y procedencia.",
          "Fuentes 210, 220 y 580 separadas. Huellas SHA-256 contra el manifiesto B02; fecha histórica declarada por el responsable.",
          "La comprobación local identifica los bytes de las fuentes conservadas; la tabla muestra las huellas verificadas en esta instalación.",
          "La identidad de bytes no acredita cobertura epidemiológica. Una descarga nueva del portal puede diferir; el corte interno histórico exacto no está acreditado.",
          "Conservar los originales y sus referencias; verificar cualquier nueva exportación antes de compararla con estos experimentos.",
          ("data/README.md", "docs/PROCEDENCIA_B02.md", "scripts/audit_csv_sources.py",
           "data/raw/Dengue_210.csv", "data/raw/Dengue_220.csv", "data/raw/Dengue_580.csv"),
          "python -B scripts/audit_csv_sources.py --source-dir data/raw\nLectura de originales; no reconstruye paneles ni resultados."),
    Phase(3, 1, "Exploración y análisis de datos",
          "Examinar variación temporal, concentración territorial y regularidad del patrón anual.",
          "Curva semanal, totales anuales, mapa de calor año/semana y perfiles normalizados. Los mapas de calor usan log(1+casos) solo para representar magnitudes.",
          "Las figuras históricas se construyen desde el panel local. No hay notebooks de EDA ni una ejecución STL registrada que respalde por sí sola las cifras documentales de fuerza estacional.",
          "EDA descriptivo del histórico completo; no es selección de variables libre de fuga ni demuestra causalidad. Rankings territoriales usan todo el periodo.",
          "Registrar estadísticas y diagnósticos reproducibles, distinguiendo exploración global de decisiones basadas solo en entrenamiento.",
          ("app/historical_app.py", "data/processed/panel_casos.parquet", "docs/ESTADO_DEL_PROYECTO.md"),
          "Laboratorio → Vistas históricas → Territorio y patrones. Requiere el panel local; no ajusta modelos.", "Territorio y patrones"),
    Phase(4, 1, "Limpieza y preparación de datos",
          "Identificar registros aceptados, descartes y ausencias sin confundir reglas históricas con el contrato nuevo.",
          "Ingesta heredada: filtra eventos/códigos, suma claves y completa ausencias con cero. B03/B05: periodos explícitos, eventos independientes y faltantes None.",
          "El reporte guardado permite inspeccionar el embudo histórico. B08 mantiene ceros observados y ausencias como estados diferentes.",
          "El histórico suma 210+220, pliega S53 en S52 y usa fechas técnicas de 52 posiciones por año. Exterior se filtra en algunas vistas, no en toda la evaluación.",
          "Resolver calendario, catálogo, cobertura y comparabilidad de eventos antes de reconstruir resultados bajo reglas nuevas.",
          ("src/episentinel/data/ingest.py", "reports/ingest_report.json", "docs/CONTRATO_SERIES_B03.md", "docs/CONTRATO_PIPELINE_B05.md"),
          "Consultar el reporte y las pruebas test_ingest.py / test_epidemiological_series.py. No ejecutar build_panel.py sobre salidas existentes.", "Panorama"),
    Phase(5, 2, "Ingeniería de características",
          "Representar los conteos con las transformaciones que realmente utilizan los métodos disponibles.",
          "SARIMA ajusta log1p(conteos), configura diferenciación y componente estacional, y devuelve expm1 con recorte no negativo. La ingenua estacional repite el desfase de 52 observaciones.",
          "La transformación y los parámetros están implementados. No existe una matriz de variables exógenas ni selección de características ejecutada.",
          "El periodo 52 es heredado y provisional frente a B03. No hay comparación ejecutada de transformaciones que permita declararla óptima.",
          "Documentar la elección y compararla en validación temporal; no añadir clima o población como variables disponibles sin datos e implementación.",
          ("src/episentinel/models/sarima.py", "src/episentinel/baselines/ingenua_estacional.py", "tests/test_sarima.py"),
          "python -B -m pytest tests/test_sarima.py tests/test_baselines.py -q -p no:cacheprovider\nPruebas de software sintéticas; no prueban eficacia real."),
    Phase(6, 2, "Dividir los datos",
          "Reservar observaciones futuras y hacer explícitos los límites de la evaluación temporal existente.",
          "Configuración: entrenamiento 2007–2020, validación 2021 y prueba 2022. El evaluador histórico ajusta con 2007–2021 y pronostica las 52 semanas de 2022.",
          "Los límites posicionales provienen del split guardado. El evaluador tiene constantes propias: no consume automáticamente esa configuración.",
          "Hay fuga en la selección territorial: build_panel.py usa entrenamiento para elegibilidad, pero ordena con todo el panel; evaluate_fase2.py elige el top 5 con todo el periodo. No se declara evaluación libre de fuga.",
          "Seleccionar series solo con entrenamiento, unificar configuración y reservar la prueba después de cerrar selección y ajuste.",
          ("configs/split.json", "scripts/build_panel.py", "scripts/evaluate_fase2.py", "configs/series_seleccionadas.csv"),
          "Contrastar split.json con los cortes y la selección en ambos scripts. La figura representa configuración, no una validación ejecutada.", "Panorama"),
    Phase(7, 2, "Seleccionar el algoritmo",
          "Contrastar baselines de pronóstico con SARIMA sin asumir de antemano un ganador.",
          "Último valor, ingenua estacional, SARIMA (1,1,1)(1,0,1)[52] y SARIMA (1,1,1) sin estacionalidad. Canal endémico y EARS son reglas de señales, no clasificadores entrenados.",
          "La comparación guardada identifica métodos evaluados y su error. No hay implementación ni resultados Prophet en el alcance disponible.",
          "La comparación utiliza una sola ventana y una selección retrospectiva de series. No demuestra superioridad general de SARIMA ni constituye selección por validación independiente.",
          "Fijar criterio de selección con validación temporal, manteniendo ambos baselines y registrando fallos por método.",
          ("reports/comparacion_fase2.csv", "scripts/evaluate_fase2.py", "src/episentinel/baselines/ingenua_estacional.py", "src/episentinel/models/sarima.py"),
          "Consultar comparacion_fase2.csv y la vista Evidencia. No regenerar esta evaluación al navegar.", "Evidencia"),
    Phase(8, 3, "Entrenar el modelo",
          "Ajustar SARIMA únicamente con el prefijo anterior al origen elegido y conservar lo necesario para reproducirlo.",
          "ajustar_sarima() delega en statsmodels SARIMAX sobre log1p. El evaluador usa órdenes fijos; el laboratorio histórico permite un ajuste retrospectivo por acción explícita.",
          "Existen métricas guardadas de ajustes históricos y código reutilizable. No hay modelo serializado ni registro completo de configuración, convergencia y pronósticos por ejecución.",
          "Una gráfica o un objeto ajustado en memoria no es un modelo persistido. Los baselines no requieren entrenamiento de parámetros.",
          "Registrar versiones, identidad de datos, parámetros, convergencia y predicciones por ejecución antes de declarar entrenamiento plenamente reproducible.",
          ("src/episentinel/models/sarima.py", "scripts/evaluate_fase2.py", "reports/comparacion_fase2.csv", "docs/BITACORA_EXPERIMENTOS.md"),
          "Vistas históricas → Pronósticos → Calcular pronóstico histórico. Solo el botón ejecuta; el resultado de sesión no se persiste como experimento.", "Pronósticos"),
    Phase(9, 3, "Ajustar hiperparámetros",
          "Elegir órdenes y parámetros mediante validación temporal reproducible, sin usar la prueba para ajustar.",
          "La entrega existente usa órdenes fijos. Alternar estacionalidad en la interfaz no implementa una búsqueda ni registra selección de hiperparámetros.",
          "No hay evidencia ejecutada de búsqueda de hiperparámetros en el alcance entregado. La bitácora no registra esta búsqueda.",
          "Comparar variantes sobre el test no es ajuste validado. Ninguna curva de optimización se presenta como resultado existente.",
          "Diseñar un espacio acotado, usar validación temporal y registrar candidatos, fallos, criterio y elección antes del test final.",
          ("src/episentinel/models/sarima.py", "scripts/evaluate_fase2.py", "docs/BITACORA_EXPERIMENTOS.md"),
          "Revisar órdenes fijos y bitácora. No existe un comando de búsqueda ejecutada para reproducir esta fase."),
    Phase(10, 3, "Evaluar el modelo",
          "Medir error de conteos futuros e incertidumbre donde los intervalos existen.",
          "MAE, RMSE y MASE con denominador estacional calculado sobre entrenamiento; cobertura del IC95 para SARIMA. Se leen métricas guardadas, no se vuelven a calcular modelos.",
          "El CSV de evaluación contiene métricas por serie y método; el resumen se deriva de ese archivo en esta instalación.",
          "Una ventana 2022, horizonte 52 y universo seleccionado retrospectivamente. Los intervalos no están disponibles en todos los métodos; una cobertura alta tampoco prueba utilidad de bandas muy anchas.",
          "Guardar pronósticos, homogeneizar universos/cortes y registrar fallos. No usar accuracy ni métricas de clasificación para estos pronósticos de conteos.",
          ("reports/comparacion_fase2.csv", "src/episentinel/evaluation/forecast_metrics.py", "scripts/evaluate_fase2.py"),
          "Consultar la tabla y las barras MASE existentes. Regenerar experimentos requiere otro incremento y salidas aisladas.", "Evidencia"),
    Phase(11, 4, "Validar que generalice",
          "Comprobar comportamiento fuera de muestra en distintos orígenes y territorios.",
          "Existe una evaluación temporal en 2022. split.json propone rolling origin de 8 semanas, paso 4; tener configuración no significa haberlo ejecutado.",
          "Solo se dispone de la ventana de prueba histórica; no hay resultados entregados de origen móvil sobre las 65 series previstas.",
          "El top 5 usa el periodo completo. Las ciudades grandes no demuestran comportamiento en municipios de difícil acceso. Las pruebas sintéticas verifican software, no generalización epidemiológica.",
          "Corregir selección, ejecutar varios orígenes con los mismos horizontes y registrar métricas/fallos por serie. Validar señales necesita etiquetas externas.",
          ("configs/split.json", "reports/comparacion_fase2.csv", "configs/series_seleccionadas.csv", "docs/ESTADO_DEL_PROYECTO.md"),
          "Consultar configuración rolling_origin y resultados de la única ventana. No existe un reporte ejecutado de origen móvil en esta entrega.", "Evidencia"),
    Phase(12, 4, "Desplegar el modelo",
          "Distinguir aplicación ejecutable, servicio analítico y modelo realmente desplegado.",
          "Plataforma unificada Streamlit; B08 consume B03/B04/B05. B06 ofrece baselines con fechas compatibles; B07 diferencia señal, sin señal y no evaluable.",
          "La ejecución local está documentada en I1. Existe código de servicios, pero el Observatorio no conecta B06/B07 ni sirve un modelo entrenado persistido.",
          "No se acredita despliegue público. B03 entrega periodos sin fechas y B06 exige fechas semanales; calendario/cobertura siguen pendientes. Las señales históricas no son B07 validado.",
          "Resolver contratos temporales, elegibilidad y versionado del modelo antes de habilitar inferencia; documentar despliegue y seguimiento cuando existan.",
          ("app/platform_app.py", "docs/PLATAFORMA_I1.md", "src/episentinel/services/forecast_service.py", "src/episentinel/services/signal_service.py", "docs/CONTRATO_SENALES_B07.md"),
          "python -B -m streamlit run app/platform_app.py --server.address 127.0.0.1 --server.port 8504\nArranque local; no publica ni despliega un modelo."),
)

EXPECTED_SOURCES = {
    "data/raw/Dengue_210.csv": "57fa15911fa360a624c3557d4593c2ad7b7de28cf44e7750325f21c771b78914",
    "data/raw/Dengue_220.csv": "541836debc708dbd2b4f429b812d44b6a337069e89d620de6afc7f479d4385eb",
    "data/raw/Dengue_580.csv": "80520bbc136acb69fbf2862dbf76499f4fd7ebe4ac3d75bdfb788c4cbfaf6854",
}


def evidence_paths():
    return tuple(sorted({p for phase in PHASES for p in phase.sources}))


def evidence_signature(root):
    root = Path(root)
    return tuple((relative, path.stat().st_mtime_ns, path.stat().st_size)
                 for relative in evidence_paths() if (path := root / relative).is_file())


def load_context(root):
    """Read named evidence only. No scripts, models, inference, or writes."""
    root = Path(root)
    context = {"available": {p: (root / p).is_file() for p in evidence_paths()},
               "sources": [], "ingest": None, "split": None, "comparison": None, "errors": []}
    for relative, expected in EXPECTED_SOURCES.items():
        path = root / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        context["sources"].append({"Archivo": path.name, "Estado": "Coincide" if digest == expected else "Ausente" if digest is None else "Huella diferente",
                                   "SHA-256 local": digest, "SHA-256 de referencia": expected})
    for key, relative in (("ingest", "reports/ingest_report.json"), ("split", "configs/split.json")):
        path = root / relative
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("Se esperaba un objeto de configuración/reporte")
                context[key] = value
            except (OSError, ValueError) as exc:
                context["errors"].append(f"{relative}: {exc}")
    path = root / "reports/comparacion_fase2.csv"
    if path.is_file():
        try:
            frame = pd.read_csv(path, dtype={"serie": str})
            required = {"serie", "modelo", "mae", "rmse", "mase"}
            if frame.empty or not required.issubset(frame.columns):
                raise ValueError("Faltan resultados o columnas de evaluación")
            for column in ("mae", "rmse", "mase"):
                frame[column] = pd.to_numeric(frame[column], errors="raise")
                if not frame[column].map(lambda x: pd.notna(x) and 0 <= x < float("inf")).all():
                    raise ValueError(f"Métrica no válida: {column}")
            if frame[["serie", "modelo"]].isna().any().any() or frame.duplicated(["serie", "modelo"]).any():
                raise ValueError("Identidades de evaluación ausentes o repetidas")
            context["comparison"] = frame
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            context["errors"].append(f"reports/comparacion_fase2.csv: {exc}")
    return context


def phase_status(phase, context):
    if phase.number == 9:
        return "Pendiente"
    if phase.number == 2 and all(row["Estado"] == "Coincide" for row in context["sources"]) and all(
        context["available"].get(p, False) for p in ("data/README.md", "docs/PROCEDENCIA_B02.md", "scripts/audit_csv_sources.py")
    ):
        return "Completo con evidencia"
    return "Parcial"


def split_rows(context):
    split = context["split"]
    if not split:
        return []
    ends = [split.get(key) for key in ("train_end", "val_end", "test_end")]
    if any(type(value) is not int for value in ends) or not 0 <= ends[0] < ends[1] < ends[2]:
        return []
    starts = (0, ends[0] + 1, ends[1] + 1)
    return [{"Conjunto": name, "Inicio (posición)": start, "Fin inclusivo": end, "Semanas configuradas": end - start + 1}
            for name, start, end in zip(("Entrenamiento", "Validación", "Prueba"), starts, ends)]


def summary_rows(context):
    frame = context["comparison"]
    if frame is None:
        return None
    return frame.groupby("modelo", sort=False)[["mae", "rmse", "mase"]].mean().sort_values("mase")
