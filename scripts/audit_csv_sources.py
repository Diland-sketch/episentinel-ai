"""Read-only reconciliation. Prints JSON; never writes historical reports."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from episentinel.data.sivigila_adapter import audit_sivigila

EXPECTED = {
    210: ("57fa15911fa360a624c3557d4593c2ad7b7de28cf44e7750325f21c771b78914", 200583, 196501, 1141400),
    220: ("541836debc708dbd2b4f429b812d44b6a337069e89d620de6afc7f479d4385eb", 21557, 21096, 43553),
    580: ("80520bbc136acb69fbf2862dbf76499f4fd7ebe4ac3d75bdfb788c4cbfaf6854", 1511, 1486, 1551),
}


# Independently pinned audit controls: (records, sum of counts), per source/category.
EXPECTED_PARTITIONS = {
    210: {"municipal_candidate": (195591, 1139070), "unknown_municipality": (3718, 6563),
          "exterior": (910, 2330), "unknown_origin": (261, 889), "exterior_unknown": (97, 150)},
    220: {"municipal_candidate": (20998, 43441), "unknown_municipality": (377, 446),
          "exterior": (98, 112), "unknown_origin": (58, 74), "exterior_unknown": (12, 13)},
    580: {"municipal_candidate": (1474, 1539), "unknown_municipality": (22, 22),
          "exterior": (12, 12), "unknown_origin": (1, 1)},
}


def partition_checks(result, expected_event):
    """Check routing independently of the adapter's classifier and legacy union.

    All records must be parsed and occur once in municipal/special/foreign.
    Malformed, duplicate or unassigned records fail closed, without imputing them.
    """
    foreign = [r for r in result.parsed if r["cod_eve"] != expected_event]
    groups = (result.candidates, result.special, foreign)
    def identity(row):
        return row["source"], row["record"]
    parsed_ids = Counter(map(identity, result.parsed))
    assigned = [r for group in groups for r in group]
    assigned_ids = Counter(map(identity, assigned))
    # Independent interpretation of the documented syntactic territorial rules.
    def expected_territory(code):
        if code == "00000":
            return "unknown_origin"
        if code == "01000":
            return "exterior_unknown"
        if code[:2] == "01":
            return "exterior"
        if code[-3:] == "000":
            return "unknown_municipality"
        return "municipal_candidate"
    def payload(row):
        return {key: value for key, value in row.items() if key != "territory"}
    originals = {identity(r): payload(r) for r in result.parsed}
    return {
        "complete_parse": (len(result.parsed) == result.rows_read and result.rows_read > 0
                           and not any(i.code in {"csv", "schema", "row_width", "empty"} for i in result.issues)),
        "no_overlap": all(n == 1 for n in assigned_ids.values()) and all(n == 1 for n in parsed_ids.values()),
        "record_conservation": assigned_ids == parsed_ids,
        "count_conservation": sum(r["conteo"] for r in assigned) == sum(r["conteo"] for r in result.parsed),
        "payload_integrity": all(originals.get(identity(r)) == payload(r) for r in assigned),
        "territorial_partition": all(
            r["cod_eve"] == expected_event and expected_territory(r["cod_mun"]) == "municipal_candidate"
            and r.get("territory") == "municipal_candidate" for r in result.candidates
        ) and all(
            r["cod_eve"] == expected_event and expected_territory(r["cod_mun"]) != "municipal_candidate"
            and r.get("territory") == expected_territory(r["cod_mun"]) for r in result.special
        ),
    }


def reconcile(source_dir, *, historical_report=None):
    summaries, all_rows, accepted, checks = [], [], [], {}
    for event, (sha, n, legacy_n, legacy_sum) in EXPECTED.items():
        result = audit_sivigila(Path(source_dir) / f"Dengue_{event}.csv", event)
        rows = result.parsed
        legacy = result.candidates + [r for r in result.special if r["territory"] == "exterior"]
        all_rows.extend(rows)
        accepted.extend(legacy)
        checks[f"source_{event}"] = (result.sha256 == sha and result.rows_read == n
                                      and len(legacy) == legacy_n and sum(r["conteo"] for r in legacy) == legacy_sum)
        integrity = partition_checks(result, event)
        checks.update({f"partition_{event}_{key}": value for key, value in integrity.items()})
        categories = {}
        for r in result.candidates + result.special:
            c = categories.setdefault(r["territory"], {"rows": 0, "count": 0})
            c["rows"] += 1
            c["count"] += r["conteo"]
        checks[f"categories_{event}"] = {
            key: (value["rows"], value["count"]) for key, value in categories.items()
        } == EXPECTED_PARTITIONS[event]
        summaries.append({"source": result.source, "sha256": result.sha256, "rows": result.rows_read,
                          "blocked": result.blocked, "categories": categories,
                          "issue_counts": dict(Counter(i.code for i in result.issues)),
                          "records_with_issues": len({i.record for i in result.issues if i.record is not None}),
                          "foreign": {"rows": sum(r["cod_eve"] != event for r in rows),
                                      "count": sum(r["conteo"] for r in rows if r["cod_eve"] != event)},
                          "issues": [asdict(i) for i in result.issues]})
    expected_events = [r for r in all_rows if r["cod_eve"] in EXPECTED]
    foreign = [r for r in all_rows if r["cod_eve"] not in EXPECTED]
    keys = Counter(tuple(r[c] for c in ("cod_eve", "ano", "semana", "cod_mun")) for r in accepted)
    report = {
        "filas_crudas": sum(s["rows"] for s in summaries),
        "filas_ajenas_excluidas": len(foreign),
        "eventos_ajenos": dict(Counter(str(r["cod_eve"]) for r in foreign)),
        "filas_tras_excluir_ajenas": len(expected_events),
        "filas_invalidas_adicionales": len(expected_events) - len(accepted),
        "filas_validas_para_panel": len(accepted),
        "filas_validas_por_evento": dict(Counter(str(r["cod_eve"]) for r in accepted)),
        "municipios_unicos_dataset_completo": len({r["cod_mun"] for r in expected_events}),
        "municipios_unicos_filas_validas": len({r["cod_mun"] for r in accepted}),
        "periodo": [min(r["ano"] for r in accepted), max(r["ano"] for r in accepted)] if accepted else None,
        "suma_conteo_casos_210_220": sum(r["conteo"] for r in accepted if r["cod_eve"] in {210, 220}),
        "suma_conteo_mortalidad_580": sum(r["conteo"] for r in accepted if r["cod_eve"] == 580),
        "filas_clave_duplicada": sum(n for n in keys.values() if n > 1),
        "filas_semana_53": sum(r["semana"] == 53 for r in accepted),
    }
    historical_path = Path(historical_report) if historical_report is not None else Path(__file__).resolve().parents[1] / "reports/ingest_report.json"
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    checks["historical_report"] = report == historical
    return {"checks": checks, "sources": summaries,
            "historical_discrepancies": {key: {"computed": report.get(key), "stored": historical.get(key)}
                                         for key in report.keys() | historical.keys() if report.get(key) != historical.get(key)}, "legacy_comparison_only": report,
            "note": "Legacy acceptance includes Exterior and excludes unknown municipalities; not a new policy."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = reconcile(args.source_dir)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if all(output["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
