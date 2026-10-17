"""CLI: ``python -m garmin_recovery run [--root .] [--dry-run] [--now ISO]``."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from .pipeline import run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="garmin_recovery")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="Genera history/, app/readiness_v3.json y app/dashboard.html")
    p_run.add_argument("--root", default=".")
    p_run.add_argument("--dry-run", action="store_true", help="Calcula e imprime sin escribir archivos")
    p_run.add_argument("--now", help="Instante ISO para reproducir un día concreto")
    p_val = sub.add_parser("validate", help="Valida JSON, informe, gráficas e historial publicados")
    p_val.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    if args.cmd == "validate":
        from .validate import validate, write_result
        res = validate(args.root)
        write_result(args.root, res)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["status"] == "ok" else 1

    now = None
    if args.now:
        now = datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo("Europe/Madrid"))
    result = run(args.root, now=now, write=not args.dry_run)
    rd = result["readiness"]
    print(json.dumps({
        "app": result["app_version"], "date": result["date"], "state": rd["state"],
        "zone": rd["zone"], "score": rd["score"], "confidence": rd["confidence"],
        "legacy_v2": result["legacy_v2"], "history_days": result["history"]["days"],
        "reasons": rd["reasons"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
