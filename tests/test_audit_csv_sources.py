"""Synthetic faults exercise reconciliation and CLI without touching originals."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from episentinel.data.sivigila_adapter import HEADERS

SPEC = importlib.util.spec_from_file_location("audit_sources", Path(__file__).resolve().parents[1] / "scripts/audit_csv_sources.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.fixture
def sources(tmp_path, monkeypatch):
    expected = {}
    partitions = {}
    for event in (210, 220, 580):
        path = tmp_path / f"Dengue_{event}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            for mun, dep, ev, count in [("5,001", "5", event, 2), ("1,862", "1", event, 3),
                                         ("0", "0", event, 5), ("5,002", "5", 999, 7)]:
                writer.writerow([ev, "EVENTO", 53, "2,020", dep, mun, "DEP", "MUN", count])
        expected[event] = (hashlib.sha256(path.read_bytes()).hexdigest(), 4, 2, 5)
        partitions[event] = {"municipal_candidate": (1, 2), "exterior": (1, 3), "unknown_origin": (1, 5)}
    monkeypatch.setattr(audit, "EXPECTED", expected)
    monkeypatch.setattr(audit, "EXPECTED_PARTITIONS", partitions)
    stored = {"filas_crudas": 12, "filas_ajenas_excluidas": 3, "eventos_ajenos": {"999": 3},
              "filas_tras_excluir_ajenas": 9, "filas_invalidas_adicionales": 3,
              "filas_validas_para_panel": 6, "filas_validas_por_evento": {"210": 2, "220": 2, "580": 2},
              "municipios_unicos_dataset_completo": 3, "municipios_unicos_filas_validas": 2,
              "periodo": [2020, 2020], "suma_conteo_casos_210_220": 10,
              "suma_conteo_mortalidad_580": 5, "filas_clave_duplicada": 0, "filas_semana_53": 6}
    report = tmp_path / "historical.json"
    report.write_text(json.dumps(stored), encoding="utf-8")
    original = audit.reconcile
    monkeypatch.setattr(audit, "reconcile", lambda folder: original(folder, historical_report=report))
    return tmp_path, report


def test_valid_partition_and_cli(sources, capsys):
    folder, _ = sources
    assert audit.main(["--source-dir", str(folder)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert all(output["checks"].values())
    assert output["historical_discrepancies"] == {}
    assert all(s["blocked"] and s["records_with_issues"] == 1 for s in output["sources"])
    assert sum(s["foreign"]["count"] for s in output["sources"]) == 21


@pytest.mark.parametrize("fault", ["swap", "overlap", "drop", "mutate_count"])
def test_partition_faults_fail_even_if_legacy_union_can_match(sources, monkeypatch, capsys, fault):
    folder, _ = sources
    original = audit.audit_sivigila
    def corrupt(*args, **kwargs):
        result = original(*args, **kwargs)
        exterior = next(r for r in result.special if r["territory"] == "exterior")
        if fault == "swap":
            municipal = result.candidates.pop()
            result.special.remove(exterior)
            municipal["territory"] = "exterior"
            exterior["territory"] = "municipal_candidate"
            result.candidates.append(exterior)
            result.special.append(municipal)
        elif fault == "overlap":
            result.special.append(result.candidates[0])
        elif fault == "drop":
            result.special.remove(next(r for r in result.special if r["territory"] == "unknown_origin"))
        else:
            result.candidates[0] = dict(result.candidates[0], conteo=100)
        return result
    monkeypatch.setattr(audit, "audit_sivigila", corrupt)
    assert audit.main(["--source-dir", str(folder)]) == 1
    output = json.loads(capsys.readouterr().out)
    checks = output["checks"]
    suffix = {"swap": "territorial_partition", "overlap": "no_overlap",
              "drop": "record_conservation", "mutate_count": "count_conservation"}[fault]
    assert not checks[f"partition_210_{suffix}"]
    if fault in {"swap", "drop"}:
        assert checks["historical_report"]  # old checks alone missed these faults


def test_historical_discrepancy_exit_one(sources, capsys):
    folder, report = sources
    stored = json.loads(report.read_text())
    stored["suma_conteo_casos_210_220"] = 11
    report.write_text(json.dumps(stored))
    assert audit.main(["--source-dir", str(folder)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["historical_discrepancies"]["suma_conteo_casos_210_220"] == {"computed": 10, "stored": 11}


def test_fingerprint_discrepancy_exit_one(sources, capsys):
    folder, _ = sources
    path = folder / "Dengue_210.csv"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert audit.main(["--source-dir", str(folder)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert not output["checks"]["source_210"] and output["checks"]["historical_report"]


@pytest.mark.parametrize("fault", ["missing", "invalid_json"])
def test_input_failures_exit_two(sources, capsys, fault):
    folder, report = sources
    if fault == "missing":
        folder = folder / "missing"
    else:
        report.write_text("{")
    assert audit.main(["--source-dir", str(folder)]) == 2
    assert "error" in json.loads(capsys.readouterr().err)


@pytest.mark.parametrize("suffix", ["bad,row\n", '"unterminated'])
def test_unparseable_record_fails_conservation(sources, capsys, suffix):
    folder, _ = sources
    with (folder / "Dengue_210.csv").open("a", encoding="utf-8") as f:
        f.write(suffix)
    assert audit.main(["--source-dir", str(folder)]) == 1
    assert not json.loads(capsys.readouterr().out)["checks"]["partition_210_complete_parse"]
