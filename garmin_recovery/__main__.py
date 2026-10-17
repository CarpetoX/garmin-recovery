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
    p_val.add_argument("--max-age-min", type=float, default=None,
                       help="Falla si la salida tiene más minutos de antigüedad (en la cadena: 60)")
    p_al = sub.add_parser("alert", help="Abre, comenta o cierra el issue de aviso en GitHub")
    p_al.add_argument("--root", default=".")
    p_al.add_argument("--scope", choices=("chain", "watchdog"), default="chain")
    p_nt = sub.add_parser("notify", help="Envía el aviso ntfy del informe nuevo (si NTFY_TOPIC está configurado)")
    p_nt.add_argument("--root", default=".")
    p_site = sub.add_parser("site", help="Genera la web publicada (GitHub Pages, instalable en el móvil)")
    p_site.add_argument("--root", default=".")
    p_site.add_argument("--out", default="_site")
    p_site.add_argument("--no-history", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "site":
        from .site import build_site
        print(json.dumps(build_site(args.root, args.out, history=not args.no_history), ensure_ascii=False))
        return 0
    if args.cmd == "notify":
        from .notify import main as notify_main
        return notify_main(args.root)
    if args.cmd == "alert":
        from .alerts import main as alert_main
        return alert_main(args.root, args.scope)
    if args.cmd == "validate":
        from .validate import validate, write_result
        res = validate(args.root, max_age_minutes=args.max_age_min)
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
