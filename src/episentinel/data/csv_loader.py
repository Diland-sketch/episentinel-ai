"""Public B04 entry point for canonical CSV; no temporal transformations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from os import PathLike
from pathlib import Path
from typing import BinaryIO

from .csv_contract import Issue, read_canonical

CONTRACT_VERSION = "1"

# Informational conditions, not epidemiological policies or CSV errors.
_PENDING_DECISIONS = (
    ("calendar", "B03: calendario, significado de semana y fechas pendientes."),
    ("week_53", "B03: tratamiento analítico de semana 53 pendiente; se conserva."),
    ("coverage", "B03: cobertura y ausencias pendientes; no se imputan ceros."),
    ("territory", "B03: catálogo territorial y política de territorios especiales pendientes."),
    ("event_comparability", "B03: comparabilidad de eventos pendiente; no se combinan."),
)


@dataclass
class CsvLoadResult:
    data: list[dict] | None
    report: dict
    blocked: bool
    pending_decisions: list[dict[str, str]]
    source: str
    sha256: str
    contract_version: str


def load_csv(
    source: str | PathLike | bytes | BinaryIO, *, source_name: str | None = None,
) -> CsvLoadResult:
    """Validate canonical CSV with B01 and expose data only for unblocked loads.

    Binary streams are read from their current position to EOF and never closed.
    I/O errors propagate; unsupported inputs (including text streams) raise
    TypeError, as does a source_name other than str or None. CSV errors are
    returned in report. No files are written.
    """
    if source_name is not None and not isinstance(source_name, str):
        raise TypeError("source_name must be str or None")

    if not isinstance(source, (str, PathLike, bytes)):
        read = getattr(source, "read", None)
        if not callable(read):
            raise TypeError("source must be a path, bytes or a binary stream")
        stream_name = getattr(source, "name", None)
        if source_name is None and isinstance(stream_name, (str, PathLike)):
            source_name = Path(stream_name).name
        source = read()
        if not isinstance(source, bytes):
            raise TypeError("binary stream read() must return bytes")

    audit = read_canonical(source, source_name=source_name)
    pending = [{"code": code, "reason": reason} for code, reason in _PENDING_DECISIONS]
    errors = [asdict(issue) for issue in audit.issues if issue.severity == "error"]
    warnings = [asdict(issue) for issue in audit.issues if issue.severity == "warning"]
    warnings.extend(
        asdict(Issue(audit.source, None, None, None, f"pending_{item['code']}",
                     item["reason"], severity="warning"))
        for item in pending
    )
    data = None if audit.blocked else [dict(row) for row in audit.candidates]
    report = {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "rows_read": audit.rows_read,
            "rows_parsed": len(audit.parsed),
            "municipal_candidates": len(audit.candidates),
            "special_records": len(audit.special),
            "rows_delivered": 0 if data is None else len(data),
            "records_with_errors": len({i["record"] for i in errors if i["record"] is not None}),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }
    return CsvLoadResult(
        data=data, report=report, blocked=audit.blocked, pending_decisions=pending,
        source=audit.source, sha256=audit.sha256, contract_version=CONTRACT_VERSION,
    )
