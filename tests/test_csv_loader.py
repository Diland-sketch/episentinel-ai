"""B04 public API and B01 compatibility, using synthetic CSV inputs."""
from dataclasses import asdict
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path

import pytest

from episentinel.data.csv_contract import read_canonical
from episentinel.data.csv_loader import CsvLoadResult, load_csv

HEADER = "cod_mun,ano,semana,cod_eve,conteo\n"
VALID = (HEADER + "05001,2020,1,210,0\n05001,2020,3,210,2\n").encode()


def sources(tmp_path, payload):
    path = tmp_path / "input.csv"
    path.write_bytes(payload)
    return path, payload, BytesIO(payload)


@pytest.mark.parametrize("payload", [
    VALID,
    b"\xef\xbb\xbf" + VALID,
    VALID.replace(b"\n", b"\r\n"),
    b'conteo,cod_eve,semana,ano,cod_mun\r\n0,210,1,2020,"05001"\r\n2,210,3,2020,"05001"\r\n',
])
def test_path_bytes_stream_equivalence_and_encodings(tmp_path, payload):
    results = [load_csv(s, source_name="input.csv") for s in sources(tmp_path, payload)]
    assert results[0] == results[1] == results[2]
    result = results[0]
    assert isinstance(result, CsvLoadResult) and not result.blocked
    assert [(r["cod_mun"], r["semana"], r["conteo"]) for r in result.data] == [
        ("05001", 1, 0), ("05001", 3, 2),
    ]
    assert result.sha256 == hashlib.sha256(payload).hexdigest()
    assert result.contract_version == "1"


@pytest.mark.parametrize("payload", [
    b"", HEADER.encode(), b"cod_mun,ano\n05001,2020\n",
    (HEADER.replace("conteo", "ano") + "05001,2020,1,210,1\n").encode(),
    (HEADER.rstrip() + ",extra\n05001,2020,1,210,1,x\n").encode(),
    (HEADER + "05001,2020\n").encode(),
    (HEADER + "05001,2020,1,210,1\n\"unterminated").encode(),
    b"\xff",
])
def test_structural_errors_are_atomic_for_all_sources(tmp_path, payload):
    results = [load_csv(s, source_name="input.csv") for s in sources(tmp_path, payload)]
    assert results[0] == results[1] == results[2]
    result = results[0]
    assert result.blocked and result.data is None and result.report["errors"]
    assert result.report["summary"]["rows_delivered"] == 0


@pytest.mark.parametrize("row,column", [
    ("5001,2020,1,210,1", "cod_mun"),
    ("05001,2020,54,210,1", "semana"),
    ("05001,20,1,210,1", "ano"),
    ("05001,2020,1,999,1", "cod_eve"),
    ("05001,2020,1,210,-1", "conteo"),
    ("05001,2020,1,210,1.5", "conteo"),
    ("05001,2020,1,210,NaN", "conteo"),
    ("05001,2020,1,210,", "conteo"),
    ("05001,2020,1,210,1e3", "conteo"),
    ('05001,"2,020",1,210,1', "ano"),
])
def test_value_errors_have_record_column_and_reason(row, column):
    result = load_csv((HEADER + row + "\n").encode(), source_name="upload.csv")
    assert result.blocked and result.data is None
    assert any(i["record"] == 2 and i["column"] == column and i["reason"]
               and i["source"] == "upload.csv" for i in result.report["errors"])


@pytest.mark.parametrize("count", [1, 2])
def test_duplicates_reject_entire_load_without_aggregation(count):
    payload = (HEADER + f"05001,2020,1,210,1\n05001,2020,1,210,{count}\n"
               + "05002,2020,1,210,5\n").encode()
    result = load_csv(payload)
    assert result.blocked and result.data is None
    errors = result.report["errors"]
    assert [(i["code"], i["record"]) for i in errors] == [("duplicate", 2), ("duplicate", 3)]
    assert result.report["summary"]["rows_parsed"] == 3
    assert result.report["summary"]["rows_delivered"] == 0


def test_valid_rows_are_not_exposed_when_another_row_is_invalid():
    result = load_csv(VALID + b"05002,2020,1,210,-1\n")
    assert result.blocked and result.data is None
    assert result.report["summary"]["municipal_candidates"] == 2
    assert result.report["summary"]["rows_delivered"] == 0


def test_week_53_events_zero_and_absence_are_preserved():
    payload = (HEADER + "05001,2020,53,210,0\n05001,2021,1,210,2\n"
               + "05001,2021,3,220,3\n05001,2021,3,580,1\n").encode()
    result = load_csv(payload)
    assert not result.blocked
    assert [(r["cod_mun"], r["ano"], r["semana"], r["cod_eve"], r["conteo"])
            for r in result.data] == [
        ("05001", 2020, 53, 210, 0), ("05001", 2021, 1, 210, 2),
        ("05001", 2021, 3, 220, 3), ("05001", 2021, 3, 580, 1),
    ]
    assert not any("fecha" in r for r in result.data)


@pytest.mark.parametrize("code", ["00000", "01000", "01862", "05000"])
def test_special_territories_keep_b01_blocking_rule(code):
    result = load_csv((HEADER + f"{code},2020,1,210,1\n").encode())
    assert result.blocked and result.data is None
    assert result.report["errors"][0]["code"] == "territory"
    assert result.report["summary"]["special_records"] == 1


@pytest.mark.parametrize("payload", [VALID, VALID + b"05002,2020,1,210,-1\n", b""])
def test_report_and_full_result_are_json_serializable(payload):
    result = load_csv(payload)
    assert json.loads(json.dumps(result.report, ensure_ascii=False)) == result.report
    assert json.loads(json.dumps(asdict(result), ensure_ascii=False)) == asdict(result)
    summary = result.report["summary"]
    assert summary["error_count"] == len(result.report["errors"])
    assert summary["warning_count"] == len(result.report["warnings"])


def test_pending_decisions_are_warnings_not_csv_errors():
    result = load_csv(VALID)
    assert not result.blocked and result.report["errors"] == []
    assert {d["code"] for d in result.pending_decisions} == {
        "calendar", "week_53", "coverage", "territory", "event_comparability",
    }
    assert {i["code"] for i in result.report["warnings"]} == {
        "pending_" + d["code"] for d in result.pending_decisions
    }
    assert all(i["severity"] == "warning" for i in result.report["warnings"])
    # Results own their diagnostics; mutation does not change future loads.
    result.pending_decisions.clear()
    result.report["warnings"].clear()
    assert len(load_csv(VALID).pending_decisions) == 5


def test_source_names_defaults_and_overrides(tmp_path):
    path, payload, stream = sources(tmp_path, VALID)
    assert load_csv(path).source == "input.csv"
    assert load_csv(str(path)).source == "input.csv"
    assert load_csv(payload).source == load_csv(stream).source == "<memory>"
    with path.open("rb") as handle:
        assert load_csv(handle).source == "input.csv"
        assert not handle.closed
    for source in sources(tmp_path, VALID):
        result = load_csv(source, source_name="custom.csv")
        assert result.source == "custom.csv"
        assert all(row["source"] == "custom.csv" for row in result.data)
        assert all(i["source"] == "custom.csv" for i in result.report["warnings"])


@pytest.mark.parametrize("source_name", [Path("input.csv"), 42, False, b"input.csv", []])
def test_invalid_source_name_is_rejected_before_reading(source_name):
    stream = BytesIO(VALID)
    with pytest.raises(TypeError, match="^source_name must be str or None$"):
        load_csv(stream, source_name=source_name)
    assert stream.tell() == 0 and not stream.closed


def test_binary_stream_is_consumed_from_current_position_and_left_open():
    stream = BytesIO(b"prefix" + VALID)
    stream.seek(6)
    result = load_csv(stream)
    assert result == load_csv(VALID)
    assert not stream.closed and stream.tell() == len(b"prefix" + VALID)
    stream.seek(6)
    assert load_csv(stream) == result


@pytest.mark.parametrize("source", [None, 42, StringIO(VALID.decode())])
def test_unsupported_inputs_raise_type_error(source):
    with pytest.raises(TypeError):
        load_csv(source)


def test_io_errors_propagate(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_csv(tmp_path / "missing.csv")

    class BrokenStream:
        def read(self):
            raise OSError("failed to read")

    with pytest.raises(OSError, match="failed to read"):
        load_csv(BrokenStream())


@pytest.mark.parametrize("payload", [VALID, VALID + b"05002,2020,1,210,-1\n"])
def test_existing_path_api_and_audit_match_public_loader(tmp_path, payload):
    path = tmp_path / "input.csv"
    path.write_bytes(payload)
    audit = read_canonical(path)
    assert audit == read_canonical(payload, source_name=path.name)
    result = load_csv(path)
    assert result.blocked == audit.blocked
    assert result.sha256 == audit.sha256 and result.source == audit.source
    assert result.report["errors"] == [asdict(i) for i in audit.issues]
    assert result.data == (None if audit.blocked else audit.candidates)


def test_loading_leaves_input_and_historical_files_unchanged(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[1]

    def historical_snapshot():
        paths = [p for folder in (repo / "data", repo / "reports")
                 for p in folder.rglob("*") if p.is_file()]
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

    path, payload, stream = sources(tmp_path, VALID)
    before = historical_snapshot()
    monkeypatch.chdir(tmp_path)
    for source in (path, payload, stream):
        assert not load_csv(source).blocked
    assert historical_snapshot() == before
    assert path.read_bytes() == payload
    assert set(tmp_path.iterdir()) == {path}
