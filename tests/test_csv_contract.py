import pytest
from episentinel.data.csv_contract import read_canonical

HEADER = "cod_mun,ano,semana,cod_eve,conteo\n"


def load(tmp_path, text, encoding="utf-8"):
    p = tmp_path / "input.csv"
    with p.open("w", encoding=encoding, newline="") as f:
        f.write(text)
    return read_canonical(p)


def test_preserve_zero_s53_and_absence(tmp_path):
    r = load(tmp_path, HEADER + "05001,2020,53,210,0\n05001,2021,1,210,2\n", "utf-8-sig")
    assert not r.blocked
    assert [(x["cod_mun"], x["semana"], x["conteo"], x["record"]) for x in r.candidates] == [("05001", 53, 0, 2), ("05001", 1, 2, 3)]
    assert len(r.candidates) == 2
    assert not any("fecha" in k for x in r.candidates for k in x)


@pytest.mark.parametrize("row,column", [
    ("5001,2020,1,210,1", "cod_mun"), ("05001,2020,0,210,1", "semana"),
    ("05001,2020,54,210,1", "semana"), ("05001,20,1,210,1", "ano"),
    ("05001,2020,1,999,1", "cod_eve"), ("05001,2020,1,210,-1", "conteo"),
    ("05001,2020,1,210,1.5", "conteo"), ("05001,2020,1,210,NaN", "conteo"),
    ("05001,2020,1,210,", "conteo"), ("05001,2020,1,210,1e3", "conteo"),
    ('05001,"2,020",1,210,1', "ano"),
])
def test_invalid_values(tmp_path, row, column):
    r = load(tmp_path, HEADER + row + "\n")
    assert r.blocked and not r.candidates
    assert any(i.column == column and i.record == 2 for i in r.issues)


@pytest.mark.parametrize("text", ["", HEADER, "cod_mun,ano\n05001,2020\n", HEADER.replace("conteo", "ano"), HEADER + "05001,2020\n", HEADER + '"unterminated'])
def test_structural_errors(tmp_path, text):
    assert load(tmp_path, text).blocked


@pytest.mark.parametrize("count", [1, 2])
def test_duplicates_never_summed(tmp_path, count):
    r = load(tmp_path, HEADER + f"05001,2020,1,210,1\n05001,2020,1,210,{count}\n")
    assert r.blocked and not r.candidates and len(r.parsed) == 2
    assert sum(i.code == "duplicate" for i in r.issues) == 2


@pytest.mark.parametrize("code", ["00000", "05000", "01862", "01000"])
def test_special_territory_is_not_canonical_municipality(tmp_path, code):
    r = load(tmp_path, HEADER + f"{code},2020,1,210,1\n")
    assert r.blocked and not r.candidates and len(r.special) == 1


def test_reordered_headers_crlf(tmp_path):
    r = load(tmp_path, 'conteo,cod_eve,semana,ano,cod_mun\r\n2,210,1,2020,"05001"\r\n')
    assert not r.blocked and r.candidates[0]["conteo"] == 2


def test_malformed_after_valid_row_still_blocks(tmp_path):
    r = load(tmp_path, HEADER + '05001,2020,1,210,1\n"broken')
    assert r.blocked and len(r.candidates) == 1
    assert any(i.code == "csv" for i in r.issues)


def test_invalid_utf8(tmp_path):
    p = tmp_path / "input.csv"
    p.write_bytes(b"\xff")
    assert read_canonical(p).blocked


@pytest.mark.parametrize("year", ["", "NaN"])
def test_unparseable_year_is_reported_once(tmp_path, year):
    r = load(tmp_path, HEADER + f"05001,{year},1,210,1\n")
    assert [(i.column, i.code) for i in r.issues] == [("ano", "integer")]
