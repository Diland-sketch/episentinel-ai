"""Conservative CSV contract: no calendars, imputation or aggregation."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

FIELDS = ("cod_mun", "ano", "semana", "cod_eve", "conteo")
EVENTS = {210, 220, 580}


@dataclass
class Issue:
    source: str
    record: int | None
    column: str | None
    value: str | None
    code: str
    reason: str
    severity: str = "error"


@dataclass
class AuditResult:
    source: str
    sha256: str
    rows_read: int = 0
    candidates: list[dict] = field(default_factory=list)
    special: list[dict] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    # Parsed records retained even when rejected (e.g. foreign events).
    parsed: list[dict] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def read_csv_records(
    path: str | Path | bytes, fields: tuple[str, ...], *, source_name: str | None = None,
):
    if isinstance(path, bytes):
        data = path
        name = "<memory>"
    else:
        path = Path(path)
        data = path.read_bytes()
        name = path.name
    name = source_name if source_name is not None else name
    result = AuditResult(name, hashlib.sha256(data).hexdigest())
    rows = []
    try:
        stream = io.StringIO(data.decode("utf-8-sig"), newline="")
        reader = csv.reader(stream, delimiter=",", quotechar='"', strict=True)
        header = next(reader, None)
        if header is None or len(header) != len(set(header)) or set(header) != set(fields):
            result.issues.append(Issue(name, 1, None, repr(header), "schema", "Exact unique headers required"))
            return result, rows
        for record, values in enumerate(reader, 2):
            result.rows_read += 1
            if len(values) != len(header):
                result.issues.append(Issue(name, record, None, repr(values), "row_width", "Unexpected number of fields"))
            else:
                rows.append((record, dict(zip(header, values))))
        if not result.rows_read:
            result.issues.append(Issue(name, None, None, None, "empty", "At least one data record required"))
    except (UnicodeDecodeError, csv.Error) as exc:
        result.issues.append(Issue(name, None, None, None, "csv", str(exc)))
    return result, rows


def add_issue(result, record, column, value, code, reason):
    result.issues.append(Issue(result.source, record, column, value, code, reason))


def parse_integer(result, record, column, value, historical=False):
    pattern = r"(?:[0-9]+|[1-9][0-9]{0,2}(?:,[0-9]{3})+)" if historical else r"[0-9]+"
    if not re.fullmatch(pattern, value):
        add_issue(result, record, column, value, "integer", "Unsigned integer required; no rounding")
        return None
    try:
        return int(value.replace(",", ""))
    except ValueError:
        add_issue(result, record, column, value, "integer", "Integer exceeds supported parsing limit")
        return None


def classify_territory(code):
    if code == "00000":
        return "unknown_origin"
    if code.startswith("01"):
        return "exterior_unknown" if code.endswith("000") else "exterior"
    if code.endswith("000"):
        return "unknown_municipality"
    return "municipal_candidate"


def route_observation(result, row):
    territory = classify_territory(row["cod_mun"])
    row["territory"] = territory
    (result.candidates if territory == "municipal_candidate" else result.special).append(row)


def check_duplicates(result):
    groups = defaultdict(list)
    for row in result.parsed:
        groups[tuple(row[c] for c in FIELDS[:-1])].append(row)
    duplicate_records = set()
    for group in groups.values():
        if len(group) > 1:
            for row in group:
                duplicate_records.add(row["record"])
                add_issue(result, row["record"], None, None, "duplicate", "Repeated event/municipality/year/week key")
    result.candidates[:] = [r for r in result.candidates if r["record"] not in duplicate_records]
    result.special[:] = [r for r in result.special if r["record"] not in duplicate_records]


def validate_observation(result, row, *, expected_event=None, columns=None):
    """Validate normalized values; report the actual source column names."""
    columns = columns or {}
    valid = True
    for column, ok, reason in (
        ("ano", 1000 <= row["ano"] <= 9999, "Four-digit year required; calendar not validated"),
        ("semana", 1 <= row["semana"] <= 53, "Week must be 1..53; year/week calendar pending"),
        ("cod_eve", row["cod_eve"] in EVENTS if expected_event is None else row["cod_eve"] == expected_event,
         "Event outside contract scope" if expected_event is None else "Event differs from source declaration"),
    ):
        if not ok:
            code = "unexpected_event" if column == "cod_eve" and expected_event is not None else "range"
            add_issue(result, row["record"], columns.get(column, column), str(row[column]), code, reason)
            valid = False
    return valid


def read_canonical(path: str | Path | bytes, *, source_name: str | None = None) -> AuditResult:
    """Return audit partitions. Callers MUST check blocked before using data."""
    result, rows = read_csv_records(path, FIELDS, source_name=source_name)
    for record, raw in rows:
        values = {c: parse_integer(result, record, c, raw[c]) for c in FIELDS[1:]}
        if values["ano"] is not None and not re.fullmatch(r"[0-9]{4}", raw["ano"]):
            add_issue(result, record, "ano", raw["ano"], "year_format", "Exactly four digits required")
            continue
        code = raw["cod_mun"]
        code_ok = bool(re.fullmatch(r"[0-9]{5}", code))
        if not code_ok:
            add_issue(result, record, "cod_mun", code, "code", "Exactly five digits required")
        if not code_ok or any(v is None for v in values.values()):
            continue
        row = dict(values, cod_mun=code, source=result.source, record=record)
        result.parsed.append(row)
        if validate_observation(result, row):
            if classify_territory(code) != "municipal_candidate":
                result.special.append(dict(row, territory=classify_territory(code)))
                add_issue(result, record, "cod_mun", code, "territory", "Canonical input requires municipal candidates")
            else:
                route_observation(result, row)
    check_duplicates(result)
    return result


# Compatibility aliases for the initial increment. New consumers use named helpers.
_read = read_csv_records
_issue = add_issue
_integer = parse_integer
_classify = classify_territory
_route = route_observation
_duplicates = check_duplicates
_validate = validate_observation
