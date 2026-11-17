"""B13 read-only checks and offline fallbacks. No downloads, fitting or writes."""
import argparse
import csv
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_COMMIT = "ef6e2e770a9f075bc73fdcb28d3bd855b44ceec9"
# Byte references for the preserved demonstration installation; never repaired here.
ARTIFACTS = {
    "data/raw/Dengue_210.csv": "57fa15911fa360a624c3557d4593c2ad7b7de28cf44e7750325f21c771b78914",
    "data/raw/Dengue_220.csv": "541836debc708dbd2b4f429b812d44b6a337069e89d620de6afc7f479d4385eb",
    "data/raw/Dengue_580.csv": "80520bbc136acb69fbf2862dbf76499f4fd7ebe4ac3d75bdfb788c4cbfaf6854",
    "data/processed/b08_demo.csv": "09ef879677aa4ada53f27c2e6f305ff55fcf12068804d4d0e78497b9c14ca6f6",
    "data/processed/b08_demo_manifest.json": "7091ae653358a11bb0da23ebeb2ec6b1a6e08bb2b300b99a7643e322ae7c0248",
    "data/processed/municipios.csv": "79c4c3181c8f9d8eac0c0a6e14228a0fe10de2084c041294f1576a28de8539db",
    "data/processed/panel_casos.parquet": "41e592e9fb548085377a1c6d7ed7de026496d8c530583ba5aaf6c80e2fee5989",
    "data/processed/panel_muertes.parquet": "d790dd0f51d0648072d461e933f6f2ead5be1bc3ca18e18bb9aa59f374df143f",
    "reports/comparacion_fase2.csv": "efa45e3adcc51d90c669bffcb9d5beef6e41d19e2edaaf40bb163782fcf94830",
    "reports/comparacion_fase2.json": "b002e512e962b84f0fe04bafb357e34e392a42ed782a727e1e340d53a3926388",
    "reports/ingest_report.json": "e380bcdefb8280a78f96196c5456dbcbfe0510529cfa0f87ca13ac49d401e4f2",
}
REQUIRED_FILES = (
    "app/platform_app.py", "app/analysis_styles.css", "app/analysis_app.py",
    "app/analysis_components.py", "app/analysis_presenter.py", "app/historical_app.py",
    "app/lab_app.py", "app/lab_evidence.py", "configs/ui_period_grids.json", "configs/split.json",
    "configs/evaluacion_b10.json", "docs/GUIA_DEMO_B13.md", "docs/DEMO_B08.md",
    "docs/CONTRATO_EVALUACION_B10.md", "docs/CONTRATO_PRONOSTICO_B06.md",
    "docs/CONTRATO_SERIES_B03.md", "docs/PROCEDENCIA_B02.md",
)
DEPENDENCIES = {
    "episentinel-ai": "episentinel", "pandas": "pandas", "numpy": "numpy",
    "statsmodels": "statsmodels", "scikit-learn": "sklearn", "pyarrow": "pyarrow",
    "openpyxl": "openpyxl", "streamlit": "streamlit", "plotly": "plotly", "pytest": "pytest",
}


def saved_results(root):
    """Raw saved rows, not a recalculation of model errors or a new evaluation."""
    with (Path(root) / "reports/comparacion_fase2.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"serie", "modelo", "mae", "rmse", "mase"}.issubset(reader.fieldnames or ()):
            raise ValueError("El CSV guardado no tiene las columnas de evaluación esperadas")
        rows = list(reader)
    if not rows:
        raise ValueError("El CSV guardado no contiene resultados")
    return rows


def positional_plan(root):
    """Reuse B10's positional example, without data, selection or fitting."""
    sys.path.insert(0, str(Path(root) / "src"))
    from episentinel.evaluation.temporal_protocol import TemporalProtocol
    from episentinel.evaluation.rolling_origin import plan_rolling_origin
    config = json.loads((Path(root) / "configs/evaluacion_b10.json").read_text(encoding="utf-8"))
    example = dict(config["positional_example"])
    example["methods"] = tuple(example["methods"])
    plan = plan_rolling_origin(TemporalProtocol(**example))
    return {"scope": "Ejemplo de planificación posicional B10; NO evaluación epidemiológica ejecutada",
            "real_execution_authorized": config["real_execution_authorized"],
            "horizon": plan.protocol.horizon, "step": plan.protocol.step,
            "methods": list(plan.protocol.methods),
            "origins": [{"partition": o.partition, "cut": o.cut, "target_start": o.target_start,
                         "target_end_exclusive": o.target_end} for o in plan.origins],
            "excluded": [{"partition": o.partition, "cut": o.cut, "reason": o.reason} for o in plan.excluded]}


def demo_coverage(root):
    sys.path.insert(0, str(Path(root) / "src"))
    from episentinel.data.epidemiological_series import CalendarMetadata, MunicipalIdentity, PeriodGrid
    from episentinel.services.isolated_pipeline import PipelineConfig, run_pipeline
    root = Path(root)
    profile = json.loads((root / "configs/ui_period_grids.json").read_text(encoding="utf-8"))["profiles"][0]
    manifest = json.loads((root / "data/processed/b08_demo_manifest.json").read_text(encoding="utf-8"))
    payload = (root / "data/processed/b08_demo.csv").read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["csv_sha256"] or manifest["profile_id"] != profile["id"]:
        raise ValueError("CSV, manifiesto y perfil no corresponden")
    coverage = {}
    for event, expected in ((210, (142, 112, 150)), (220, (2, 2, None))):
        config = PipelineConfig(profile["config_version"], MunicipalIdentity("76001"), (event,),
                                PeriodGrid(profile["periods"], CalendarMetadata(**profile["calendar_metadata"])))
        result = run_pipeline(payload, config=config, source_name="b08_demo.csv")
        if result.status != "completed" or result.series is None:
            raise ValueError(f"B05 no construyó la serie {event}")
        series = result.series.series[0]
        values = tuple(point.observed_count for point in series.points)
        if values != expected or result.load_diagnostic.sha256 != manifest["csv_sha256"]:
            raise ValueError(f"Observaciones o trazabilidad inesperadas para {event}")
        coverage[event] = {"values": values, "observed": series.coverage.observed_periods,
                           "expected": series.coverage.expected_periods,
                           "calendar": profile["calendar_metadata"]["verification"]}
    return coverage


def inspect(root=ROOT, *, environment=True):
    root = Path(root).resolve()
    checks = []
    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})
    add("Python", "ok" if sys.version_info >= (3, 10) else "error", sys.version.split()[0])
    try:
        git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True)
        add("Commit de trabajo", "ok" if git.stdout.strip() == REFERENCE_COMMIT else "warning", git.stdout.strip())
        status = subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        add("Cambios locales", "warning" if status else "ok", status or "Árbol limpio")
    except (OSError, subprocess.SubprocessError) as exc:
        add("Git", "error", str(exc))
    if environment:
        for distribution, module in DEPENDENCIES.items():
            try:
                version = importlib.metadata.version(distribution)
                importlib.import_module(module)
                add("Dependencia " + distribution, "ok", version)
            except Exception as exc:
                add("Dependencia " + distribution, "error", f"{type(exc).__name__}: {exc}")
    else:
        add("Dependencias", "warning", "No comprobadas en esta llamada de prueba")
    for relative in REQUIRED_FILES:
        add(relative, "ok" if (root / relative).is_file() else "error", "Disponible" if (root / relative).is_file() else "Ausente; no se genera automáticamente")
    for relative, expected in ARTIFACTS.items():
        try:
            path = root / relative
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            add(relative, "ok" if actual == expected else "error", f"{path.stat().st_size} bytes · SHA-256 {actual}")
        except OSError as exc:
            add(relative, "error", str(exc))
    try:
        styles = (root / "app/analysis_styles.css").read_text(encoding="utf-8")
        valid = all(color in styles for color in ("#102F3A", "#276D70", "#8DCABA", "#D59A70", "#F7F5EF"))
        valid = valid and "<style>" in styles and "</style>" in styles and "https://" not in styles and "http://" not in styles
        add("Estilos locales", "ok" if valid else "error", "Identidad local sin URL externa; el renderizado se comprueba en navegador")
        coverage = demo_coverage(root)
        add("Demo real B04 → B05 → B03", "ok", json.dumps(coverage, ensure_ascii=False))
        rows = saved_results(root)
        add("Evaluación histórica guardada", "ok", f"{len(rows)} filas · {len({r['serie'] for r in rows})} series · {len({r['modelo'] for r in rows})} métodos; no se recalculan")
        plan = positional_plan(root)
        add("Plan B10", "ok", f"{len(plan['origins'])} orígenes y {len(plan['excluded'])} colas excluidas; solo planificación, sin fechas ni modelos")
    except (OSError, ValueError, KeyError, IndexError, TypeError, ImportError) as exc:
        add("Coherencia de la demostración", "error", f"{type(exc).__name__}: {exc}")
    verdict = "NO APTO" if any(c["status"] == "error" for c in checks) else "APTO CON OBSERVACIONES" if any(c["status"] == "warning" for c in checks) else "APTO"
    return {"root": str(root), "reference_commit": REFERENCE_COMMIT, "verdict": verdict, "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--saved-results", action="store_true", help="Imprime las filas guardadas, solo biblioteca estándar")
    mode.add_argument("--plan-b10", action="store_true", help="Plan posicional ilustrativo; nunca ejecuta modelos")
    parser.add_argument("--json", action="store_true", help="Informe por stdout; no crea archivos")
    args = parser.parse_args(argv)
    try:
        if args.saved_results:
            rows = saved_results(args.root)
            print("RESULTADOS HISTÓRICOS GUARDADOS · NO pertenecen a la carga del Observatorio")
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            return 0
        if args.plan_b10:
            print(json.dumps(positional_plan(args.root), ensure_ascii=False, indent=2))
            return 0
        report = inspect(args.root)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"B13 — {report['verdict']}\nRaíz: {report['root']}\nReferencia: {report['reference_commit']}")
            for check in report["checks"]:
                print(f"[{check['status'].upper()}] {check['check']}: {check['detail']}")
        return 1 if report["verdict"] == "NO APTO" else 0
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(f"NO APTO: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Windows redirected consoles may default to cp1252; diagnostics must remain printable.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
