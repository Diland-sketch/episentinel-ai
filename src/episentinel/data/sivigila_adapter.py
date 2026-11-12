"""Read original SIVIGILA exports without changing epidemiological meaning."""
from pathlib import Path
from .csv_contract import (
    AuditResult, EVENTS, read_csv_records, parse_integer, add_issue,
    validate_observation, route_observation, check_duplicates,
)

HEADERS = ("COD_EVE", "Nombre_evento", "SEMANA", "ANO", "COD_DPTO_O", "COD_MUN_O",
           "Departamento_ocurrencia", "Municipio_ocurrencia", "conteo")


def audit_sivigila(path: str | Path, expected_event: int) -> AuditResult:
    if expected_event not in EVENTS:
        raise ValueError("Unsupported expected event")
    result, rows = read_csv_records(path, HEADERS)
    for record, raw in rows:
        mapping = {"cod_eve": "COD_EVE", "ano": "ANO", "semana": "SEMANA",
                   "department": "COD_DPTO_O", "municipality": "COD_MUN_O", "conteo": "conteo"}
        values = {k: parse_integer(result, record, c, raw[c], historical=True) for k, c in mapping.items()}
        if any(v is None for v in values.values()):
            continue
        dep, mun = values.pop("department"), values.pop("municipality")
        code = dep * 1000 + mun if mun < 1000 else mun
        if not (0 <= dep <= 99 and 0 <= code <= 99999) or (mun >= 1000 and code // 1000 != dep):
            add_issue(result, record, "COD_MUN_O", raw["COD_MUN_O"], "code", "Invalid or inconsistent territorial code")
            continue
        row = dict(values, cod_mun=f"{code:05d}", source=result.source, record=record,
                   nombre_evento=raw["Nombre_evento"], departamento=raw["Departamento_ocurrencia"],
                   municipio=raw["Municipio_ocurrencia"])
        result.parsed.append(row)
        valid = validate_observation(result, row, expected_event=expected_event, columns=mapping)
        if valid:
            route_observation(result, row)
    check_duplicates(result)
    return result
