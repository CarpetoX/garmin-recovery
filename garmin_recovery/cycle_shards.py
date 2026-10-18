#!/usr/bin/env python3
"""Garmin Recovery V2.9.6, fase 1: copia fragmentada, íntegra y reversible.

No edita ni elimina report_cycles.json. Todos los registros se conservan.
Uso:
  python cycle_shards_v296.py --audit --ledger report_cycles.json
  python cycle_shards_v296.py --prepare --ledger report_cycles.json --archive-dir cycle_ledger_shards_v296
  python cycle_shards_v296.py --verify --ledger report_cycles.json --archive-dir cycle_ledger_shards_v296
  python cycle_shards_v296.py --restore --archive-dir cycle_ledger_shards_v296 --out restored_cycles_v296.json

Archivar NO significa que ya se pueda sustituir el ledger en producción.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path

VERSION = "2.9.6"
DEFAULT_LIMIT_BYTES = 512 * 1024
MAX_SHARDS = 100_000
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_SHARD = re.compile(r"^shards/(\d{4}-\d{2}-\d{2})/(\d{4})\.json$")


class ShardError(ValueError):
    pass


def canonical_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n").encode("utf-8")


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _valid_cycle(row):
    if not isinstance(row, dict):
        raise ShardError("Certificado no es objeto JSON")
    cid = row.get("cycle_id")
    slot = row.get("slot_at")
    if not isinstance(cid, str) or not cid or not isinstance(slot, str):
        raise ShardError("Certificado sin cycle_id/slot_at")
    if not RE_DATE.fullmatch(slot[:10]):
        raise ShardError("slot_at no tiene fecha ISO: " + cid)
    try:
        date.fromisoformat(slot[:10])
    except ValueError as exc:
        raise ShardError("Fecha de ciclo inválida: " + cid) from exc
    snapshot = row.get("snapshot")
    if snapshot is None:
        if row.get("legacy_without_snapshot") is not True or row.get("snapshot_sha256") is not None:
            raise ShardError("Snapshot perdido sin marca legacy: " + cid)
    elif not isinstance(snapshot, dict) or canonical_hash(snapshot) != row.get("snapshot_sha256"):
        raise ShardError("SHA-256 del snapshot inválido: " + cid)
    return slot[:10]


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or not isinstance(ledger.get("cycles"), list):
        raise ShardError("Ledger: se esperaba objeto con lista cycles")
    rows = ledger["cycles"]
    if type(ledger.get("count")) is not int or ledger["count"] != len(rows):
        raise ShardError("Ledger: count no coincide con cycles")
    seen = set()
    for row in rows:
        _valid_cycle(row)
        if row["cycle_id"] in seen:
            raise ShardError("cycle_id duplicado: " + row["cycle_id"])
        seen.add(row["cycle_id"])
    if ledger.get("schema_version") != 2:
        raise ShardError("Ledger: se exige schema_version=2")
    return rows


def load_source(path):
    path = Path(path)
    try:
        blob = path.read_bytes()
        ledger = json.loads(blob)
        validate_ledger(ledger)
    except (OSError, ValueError) as exc:
        raise ShardError("No se pudo validar el histórico: " + str(exc)) from exc
    return ledger, blob


def audit(ledger_path):
    ledger, blob = load_source(ledger_path)
    return {
        "version": VERSION, "status": "source_validated",
        "cycle_count": len(ledger["cycles"]),
        "snapshot_count": sum(isinstance(c.get("snapshot"), dict) for c in ledger["cycles"]),
        "legacy_count": sum(c.get("legacy_without_snapshot") is True for c in ledger["cycles"]),
        "source_bytes": len(blob),
        "source_sha256": sha_bytes(blob),
        "cycles_digest_sha256": canonical_hash(ledger["cycles"]),
        "source_unchanged": True,
    }


def _make_shard(day, first_index, cycles):
    return {"schema_version": 1, "day": day, "first_index": first_index,
            "count": len(cycles), "cycles": cycles}


def _batches(rows, byte_limit):
    if type(byte_limit) is not int or byte_limit < 1024 or byte_limit > 1024 * 1024:
        raise ShardError("Tamaño de fragmento inválido (entre 1 KB y 1 MB)")
    batches = []
    day, entries, first = None, [], 0
    for i, row in enumerate(rows):
        row_day = _valid_cycle(row)
        if day != row_day and entries:
            batches.append((day, first, entries))
            day, entries = None, []
        if not entries:
            day, first = row_day, i
        candidate = entries + [row]
        if len(encoded(_make_shard(day, first, candidate))) > byte_limit:
            if not entries:
                raise ShardError(f"Ciclo {row['cycle_id']} supera el límite individual; no dividir silenciosamente")
            batches.append((day, first, entries))
            day, first, entries = row_day, i, [row]
            if len(encoded(_make_shard(day, first, entries))) > byte_limit:
                raise ShardError("Fragmento individual supera el límite")
        else:
            entries = candidate
    if entries:
        batches.append((day, first, entries))
    if len(batches) > MAX_SHARDS:
        raise ShardError("Demasiados fragmentos")
    return batches


def verify_archive(archive_dir, source=None):
    root = Path(archive_dir)
    manifest_path = root / "index.json"
    try:
        manifest = json.loads(manifest_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ShardError("Índice del archivo no legible") from exc
    if not isinstance(manifest, dict) or manifest.get("version") != VERSION or manifest.get("format") != "ordered_shards_v1":
        raise ShardError("Versión/estructura de índice no válida")
    descs = manifest.get("shards")
    meta = manifest.get("root_metadata")
    if not isinstance(descs, list) or not isinstance(meta, dict) or len(descs) > MAX_SHARDS:
        raise ShardError("Índice mal formado")
    total = 0
    records = []
    seen = set()
    limit = manifest.get("max_shard_bytes")
    if type(limit) is not int or not 1024 <= limit <= 1024 * 1024:
        raise ShardError("Límite de fragmentos inválido")
    for desc in descs:
        if not isinstance(desc, dict):
            raise ShardError("Descriptor de fragmento inválido")
        rel = desc.get("path")
        if not isinstance(rel, str) or not RE_SHARD.fullmatch(rel):
            raise ShardError("Ruta de fragmento no permitida")
        m = RE_SHARD.fullmatch(rel)
        try:
            if not RE_DATE.fullmatch(m.group(1)):
                raise ValueError()
            date.fromisoformat(m.group(1))
        except ValueError as exc:
            raise ShardError("Fecha de fragmento inválida") from exc
        f = root / rel
        try:
            blob = f.read_bytes()
        except OSError as exc:
            raise ShardError("Falta fragmento: " + rel) from exc
        if len(blob) > limit or sha_bytes(blob) != desc.get("file_sha256"):
            raise ShardError("Tamaño/SHA-256 de fragmento incorrecto: " + rel)
        try:
            shard = json.loads(blob)
        except ValueError as exc:
            raise ShardError("JSON de fragmento inválido: " + rel) from exc
        if (not isinstance(shard, dict) or shard.get("schema_version") != 1
                or shard.get("day") != m.group(1) or shard.get("first_index") != total
                or not isinstance(shard.get("cycles"), list)
                or shard.get("count") != len(shard["cycles"])
                or shard["count"] != desc.get("count")
                or desc.get("first_index") != total
                or canonical_hash(shard) != desc.get("payload_sha256")):
            raise ShardError("Fragmento incoherente: " + rel)
        for c in shard["cycles"]:
            if _valid_cycle(c) != shard["day"]:
                raise ShardError("Ciclo archivado en día incorrecto: " + rel)
            if c["cycle_id"] in seen:
                raise ShardError("Ciclo duplicado entre fragmentos")
            seen.add(c["cycle_id"])
        if shard["cycles"]:
            if shard["cycles"][0]["cycle_id"] != desc.get("first_cycle_id") or shard["cycles"][-1]["cycle_id"] != desc.get("last_cycle_id"):
                raise ShardError("IDs del índice no coinciden: " + rel)
        records.extend(shard["cycles"])
        total += len(shard["cycles"])
    if total != manifest.get("cycle_count") or total != meta.get("count"):
        raise ShardError("Número total de certificados incorrecto")
    if canonical_hash(records) != manifest.get("cycles_digest_sha256"):
        raise ShardError("Huella SHA-256 global del histórico incorrecta")
    reconstructed = dict(meta, cycles=records)
    validate_ledger(reconstructed)
    if canonical_hash(reconstructed) != manifest.get("ledger_digest_sha256"):
        raise ShardError("El histórico reconstruido no coincide con el índice")
    if source is not None:
        original, blob = load_source(source)
        if (sha_bytes(blob) != manifest.get("source_file_sha256")
                or canonical_hash(original) != canonical_hash(reconstructed)):
            raise ShardError("El histórico reconstruido no coincide con el ORIGINAL actual")
    return reconstructed, {
        "version": VERSION, "status": "verified",
        "cycle_count": total, "shard_count": len(descs),
        "source_consistent": source is not None,
        "no_source_mutation": True,
    }


def prepare(source, archive_dir, byte_limit=DEFAULT_LIMIT_BYTES):
    source = Path(source)
    archive = Path(archive_dir)
    ledger, original_bytes = load_source(source)
    if archive.exists():
        raise ShardError("El directorio destino ya existe; nunca sobrescribir copias")
    archive.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".cycle-shards-v296-", dir=archive.parent))
    try:
        batch = _batches(ledger["cycles"], byte_limit)
        descriptors = []
        day_counts = {}
        for day, first, entries in batch:
            day_counts[day] = day_counts.get(day, 0) + 1
            part_no = day_counts[day]
            if part_no > 9999:
                raise ShardError("Demasiados fragmentos para un mismo día")
            relative = f"shards/{day}/{part_no:04d}.json"
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = _make_shard(day, first, entries)
            raw = encoded(payload)
            if len(raw) > byte_limit:
                raise ShardError("Fragmento excede límite de tamaño")
            target.write_bytes(raw)
            descriptors.append({
                "path": relative, "day": day, "first_index": first,
                "count": len(entries), "file_sha256": sha_bytes(raw),
                "payload_sha256": canonical_hash(payload),
                "first_cycle_id": entries[0]["cycle_id"],
                "last_cycle_id": entries[-1]["cycle_id"],
            })
        meta = {k: v for k, v in ledger.items() if k != "cycles"}
        index = {
            "version": VERSION, "format": "ordered_shards_v1",
            "purpose": "Verifiable NON-destructive mirror; not yet production storage",
            "source_file_sha256": sha_bytes(original_bytes),
            "source_file_bytes": len(original_bytes),
            "ledger_digest_sha256": canonical_hash(ledger),
            "cycles_digest_sha256": canonical_hash(ledger["cycles"]),
            "root_metadata": meta, "cycle_count": len(ledger["cycles"]),
            "max_shard_bytes": byte_limit, "shards": descriptors,
            "migration_state": "staged_read_only",
        }
        (temp / "index.json").write_bytes(encoded(index))
        verify_archive(temp, source)
        if source.read_bytes() != original_bytes:
            raise ShardError("El histórico original cambió durante el archivado")
        if archive.exists():
            raise ShardError("Destino apareció mientras se preparaba")
        temp.rename(archive)
        temp = None
        return {"version": VERSION, "status": "prepared_and_verified",
                "shard_count": len(descriptors), "cycle_count": len(ledger["cycles"]),
                "source_unchanged": True, "archive_dir": str(archive),
                "production_cutover": False}
    finally:
        if temp is not None and temp.exists():
            shutil.rmtree(temp)


def restore(archive_dir, output_path, source=None):
    output_path = Path(output_path)
    if output_path.exists():
        raise ShardError("Destino de restauración existente; no se sobrescribe")
    ledger, report = verify_archive(archive_dir, source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("xb") as file:
            file.write(encoded(ledger))
            file.flush()
            os.fsync(file.fileno())
        restored = json.loads(output_path.read_bytes())
        if canonical_hash(restored) != canonical_hash(ledger):
            raise ShardError("Restauración no idéntica semánticamente")
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise
    return {**report, "status": "restored_and_verified", "restored_to": str(output_path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--restore", action="store_true")
    parser.add_argument("--ledger", default="report_cycles.json")
    parser.add_argument("--archive-dir", default="cycle_ledger_shards_v296")
    parser.add_argument("--max-shard-bytes", type=int, default=DEFAULT_LIMIT_BYTES)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.audit:
        result = audit(args.ledger)
    elif args.prepare:
        result = prepare(args.ledger, args.archive_dir, args.max_shard_bytes)
    elif args.verify:
        _, result = verify_archive(args.archive_dir, args.ledger)
    else:
        if args.out is None:
            parser.error("--restore requiere --out")
        result = restore(args.archive_dir, args.out, args.ledger)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    try:
        main()
    except ShardError as e:
        raise SystemExit("V2.9.6: " + str(e)) from e
