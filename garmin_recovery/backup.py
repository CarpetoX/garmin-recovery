"""Copia de seguridad mensual de los datos que no se pueden regenerar.

Empaqueta, en un tar.gz con manifiesto SHA-256, solo una lista cerrada de archivos de datos (historial,
RPE registrado, ciclos certificados y series de Garmin). Nunca incluye secretos ni código. El workflow
`backup-monthly.yml` la sube como Release y conserva las últimas ``KEEP`` copias.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from datetime import datetime
from pathlib import Path

KEEP = 12
INCLUDE = (
    "history/daily.csv", "history/sessions.csv", "history/reports.csv", "history/model_predictions.csv",
    "training_feedback.json", "crossfit_insights.json", "report_cycles.json", "report_history.json",
    "activities.json", "wellness.json", "shift_calendar.json",
    "garmin_sleep_history.json", "garmin_heart_rate.json", "garmin_hr_timeline.json", "garmin_hrv_timeline.json",
    "garmin_extended.json", "garmin_stress.json", "garmin_body_battery.json",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(root, out_dir, now: datetime) -> dict:
    root, out_dir = Path(root), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"garmin-recovery-backup-{now:%Y-%m}.tar.gz"
    manifest = {"created_at": now.isoformat(), "files": {}, "missing": []}
    with tarfile.open(out_dir / name, "w:gz") as tar:
        for rel in INCLUDE:
            p = root / rel
            if not p.is_file():
                manifest["missing"].append(rel)
                continue
            data = p.read_bytes()
            manifest["files"][rel] = {"bytes": len(data), "sha256": _sha(data)}
            info = tarfile.TarInfo(rel)
            info.size = len(data)
            info.mtime = int(p.stat().st_mtime)
            tar.addfile(info, io.BytesIO(data))
        raw = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
        info = tarfile.TarInfo("MANIFEST.json")
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    return {"archive": str(out_dir / name), "tag": f"backup-{now:%Y-%m}", "files": len(manifest["files"]),
            "missing": manifest["missing"]}


def verify(archive) -> list[str]:
    """Problemas encontrados al comprobar el manifiesto de una copia (lista vacía = correcta)."""
    problems = []
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        if "MANIFEST.json" not in names:
            return ["falta MANIFEST.json"]
        manifest = json.loads(tar.extractfile("MANIFEST.json").read())
        for rel, meta in manifest["files"].items():
            if rel not in names:
                problems.append(f"falta {rel}")
            elif _sha(tar.extractfile(rel).read()) != meta["sha256"]:
                problems.append(f"hash distinto en {rel}")
    return problems


def tags_to_prune(tags: list[str], keep: int = KEEP) -> list[str]:
    """Etiquetas `backup-AAAA-MM` más antiguas que las ``keep`` últimas."""
    valid = sorted(t for t in tags if len(t) == 14 and t.startswith("backup-") and t[7:11].isdigit() and t[11] == "-" and t[12:].isdigit())
    return valid[:-keep] if len(valid) > keep else []


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = argv[argv.index("--out") + 1] if "--out" in argv else "dist"
    if "--prune" in argv:   # lee etiquetas por stdin, imprime las que hay que borrar
        for tag in tags_to_prune(sys.stdin.read().split()):
            print(tag)
        return 0
    res = build(".", out, datetime.now().astimezone())
    problems = verify(res["archive"])
    print(json.dumps({**res, "problems": problems}, ensure_ascii=False))
    return 1 if problems or res["files"] == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
