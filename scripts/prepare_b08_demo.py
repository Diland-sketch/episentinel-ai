"""Prepare a small, declared derivative of audited references; no original edits.

Real CSV and row-level provenance stay under an explicitly ignored output directory.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from episentinel.data.csv_loader import load_csv
from episentinel.data.sivigila_adapter import audit_sivigila
from scripts.audit_csv_sources import EXPECTED


def prepare(source_dir, output_dir):
    output_dir = Path(output_dir).resolve()
    outputs = [output_dir / "b08_demo.csv", output_dir / "b08_demo_manifest.json"]
    # No accidental publication of real observations outside ignored data locations.
    for target in outputs:
        checked = subprocess.run(["git", "check-ignore", "--quiet", str(target)], cwd=ROOT, capture_output=True)
        if checked.returncode != 0:
            raise ValueError("Output must be inside an ignored repository data directory")
    profile = json.loads((ROOT / "configs/ui_period_grids.json").read_text(encoding="utf-8"))["profiles"][0]
    periods = {tuple(p) for p in profile["periods"]}
    selected, sources = [], []
    for event in (210, 220):
        path = Path(source_dir) / f"Dengue_{event}.csv"
        result = audit_sivigila(path, event)
        if result.sha256 != EXPECTED[event][0]:
            raise ValueError(f"Original fingerprint mismatch: {path.name}")
        if any(i.code != "unexpected_event" for i in result.issues):
            raise ValueError(f"Unexpected original issues: {path.name}")
        selected.extend(dict(r) for r in result.candidates
                        if r["cod_mun"] == "76001" and (r["ano"], r["semana"]) in periods)
        sources.append({"file": path.name, "sha256": result.sha256,
                        "known_foreign_records_excluded": len(result.issues)})
    selected.sort(key=lambda r: (r["ano"], r["semana"], r["cod_eve"]))
    if not selected or {tuple(p) for p in profile["periods"]} != {(r["ano"], r["semana"]) for r in selected}:
        raise ValueError("Every declared demonstration period must have source evidence")
    text = io.StringIO(newline="")
    fields = ("cod_mun", "ano", "semana", "cod_eve", "conteo")
    writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: r[k] for k in fields} for r in selected)
    payload = text.getvalue().encode("utf-8")
    loaded = load_csv(payload, source_name="b08_demo.csv")
    if loaded.blocked:
        raise ValueError("Derived canonical CSV failed B04 validation")
    manifest = {"dataset_id": "4hyg-wa9d", "dataset_url": "https://www.datos.gov.co/Salud-y-Protecci-n-Social/Datos-de-Vigilancia-en-Salud-P-blica-de-Colombia/4hyg-wa9d/about_data",
        "attribution": "Instituto Nacional de Salud - INS, Bogotá D.C.",
        "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "download_date_declared_by_project_owner": "2026-09-23", "profile_id": profile["id"],
        "calendar_verification": "unverified", "csv_sha256": hashlib.sha256(payload).hexdigest(),
        "sources": sources, "rows": len(selected),
        "transformation": "Explicit subset: municipal candidates, cod_mun=76001, events=210/220, declared periods only; historical numeric parsing via B02 adapter; canonical columns only. No added counts, dates, zeros or records. Does not accept the full historical sources as valid canonical uploads.",
        "source_refs": [{"output_record": i, "original_file": r["source"], "original_record": r["record"],
                         "cod_eve": r["cod_eve"], "ano": r["ano"], "semana": r["semana"]}
                        for i, r in enumerate(selected, 2)]}
    contents = [payload, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")]
    for target, content in zip(outputs, contents):
        if target.exists() and target.read_bytes() != content:
            raise FileExistsError(f"Refusing to overwrite different file: {target}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for target, content in zip(outputs, contents):
        if not target.exists():
            target.write_bytes(content)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = prepare(args.source_dir, args.output_dir)
    print(json.dumps({"rows": manifest["rows"], "csv_sha256": manifest["csv_sha256"],
                      "profile_id": manifest["profile_id"]}, indent=2))
