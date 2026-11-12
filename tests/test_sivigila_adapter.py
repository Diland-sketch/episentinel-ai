import csv
import pytest
from episentinel.data.sivigila_adapter import HEADERS, audit_sivigila


def write(tmp_path, rows):
    p = tmp_path / "original.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADERS)
        w.writerows(rows)
    return p


def row(mun="5,001", dep="5", event="210", count="2", week="53"):
    return [event, "DENGUE", week, "2,020", dep, mun, "ANTIOQUIA", "Nombre, con coma", count]


def test_partition_and_conservation(tmp_path):
    p = write(tmp_path, [row(), row("1"), row("5,000"), row("1,862", "1"), row("0", "0"), row("1,000", "1"), row(event="831")])
    r = audit_sivigila(p, 210)
    assert len(r.candidates) == 0  # full and local municipality codes collide
    assert len(r.special) == 4
    assert len(r.parsed) == 7
    assert {i.record for i in r.issues if i.code == "duplicate"} == {2, 3}
    assert {x["territory"] for x in r.special} == {"unknown_municipality", "exterior", "unknown_origin", "exterior_unknown"}
    assert sum(x["conteo"] for x in r.parsed) == 14
    assert r.parsed[0]["municipio"] == "Nombre, con coma"


def test_preserves_event_week_and_count(tmp_path):
    r = audit_sivigila(write(tmp_path, [row(count="0"), row(event="220", week="1")]), 210)
    assert r.blocked
    assert len(r.candidates) == 1
    assert r.candidates[0]["semana"] == 53 and r.candidates[0]["conteo"] == 0
    assert r.parsed[1]["cod_eve"] == 220


@pytest.mark.parametrize("values", [row("68,001"), row("5,001.5"), row(count="-1"), row(count="1,2"), row(week="54")])
def test_invalid_historical_values(tmp_path, values):
    r = audit_sivigila(write(tmp_path, [values]), 210)
    assert r.blocked and not r.candidates


def test_repeatable_local_code(tmp_path):
    p = write(tmp_path, [row("1")])
    a, b = audit_sivigila(p, 210), audit_sivigila(p, 210)
    assert a == b and not a.blocked
    assert a.candidates[0]["cod_mun"] == "05001"


def test_invalid_utf8(tmp_path):
    p = tmp_path / "invalid.csv"
    p.write_bytes(b"\xff")
    r = audit_sivigila(p, 210)
    assert r.blocked and r.issues[0].code == "csv"


@pytest.mark.parametrize("event", ["831", "220"])
def test_foreign_event_has_one_source_column_issue(tmp_path, event):
    r = audit_sivigila(write(tmp_path, [row(event=event)]), 210)
    assert [(i.code, i.column, i.record) for i in r.issues] == [("unexpected_event", "COD_EVE", 2)]
    assert len(r.parsed) == 1 and not r.candidates and r.blocked


def test_range_error_names_original_column(tmp_path):
    r = audit_sivigila(write(tmp_path, [row(week="54")]), 210)
    assert [(i.code, i.column) for i in r.issues] == [("range", "SEMANA")]
