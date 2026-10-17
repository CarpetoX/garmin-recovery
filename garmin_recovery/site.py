"""Web publicada en GitHub Pages: el panel instalable como app (PWA).

``python -m garmin_recovery site --out _site`` genera, a partir de lo ya publicado en el
repositorio (``app/readiness_v3.json``, ``history/reports.csv``, ``crossfit_insights.json``
y el historial de Git de ``app/informe.md``):

* ``index.html``: el panel con calendario, RPE, semana, fuerza, puntualidad e histórico;
* ``manifest.webmanifest``, ``sw.js`` e iconos PNG: instalable en el móvil y usable sin red
  (muestra el último panel descargado);
* ``informe_semanal.md`` y ``charts/`` copiados tal cual, para enlazarlos.

Solo biblioteca estándar. No toca ``app/`` ni ``history/``.
"""
from __future__ import annotations

import csv
import json
import shutil
import struct
import subprocess
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
REPO_URL = "https://github.com/CarpetoX/garmin-recovery"


# ------------------------------------------------------------------ icono PNG (sin dependencias)
def icon_png(size: int) -> bytes:
    """Icono: fondo azul redondeado con un pulso blanco (línea de ECG)."""
    bg, fg = (42, 120, 214), (255, 255, 255)
    r = size * 0.22
    pts = [(0.14, 0.56), (0.36, 0.56), (0.45, 0.34), (0.55, 0.76), (0.63, 0.48), (0.70, 0.56), (0.86, 0.56)]
    pts = [(x * size, y * size) for x, y in pts]
    width = size * 0.065

    def near_line(px, py):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
            dx, dy = x2 - x1, y2 - y1
            t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
            if (px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2 <= (width / 2) ** 2:
                return True
        return False

    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            cx = min(max(x + 0.5, r), size - r)
            cy = min(max(y + 0.5, r), size - r)
            inside = (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r
            if not inside:
                row += bytes((0, 0, 0, 0))
            else:
                row += bytes((*(fg if near_line(x + 0.5, y + 0.5) else bg), 255))
        rows.append(bytes(row))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
            + chunk(b"IEND", b""))


MANIFEST = {
    "name": "Garmin Recovery · Rendimiento y recuperación", "short_name": "Recuperación",
    "lang": "es", "start_url": "./", "scope": "./", "display": "standalone",
    "background_color": "#f6f6f4", "theme_color": "#2a78d6",
    "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
              {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
}

SERVICE_WORKER = """// Red primero (siempre el último informe); sin red, la última copia guardada.
const CACHE = 'garmin-recovery-v1';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('garmin-recovery-') && k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match('index.html'))));
});
"""


# ------------------------------------------------------------------ histórico desde Git
def report_history(root: Path, days: int = 30, limit: int = 60, run=subprocess.run) -> list[dict]:
    """Versiones publicadas de ``app/informe.md`` (una por ciclo) con su enlace en GitHub."""
    since = (datetime.now(TZ) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        out = run(["git", "-C", str(root), "log", f"--since={since}", "--format=%H %cI", "--", "app/informe.md"],
                  capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    items = []
    for line in out.splitlines()[:limit]:
        try:
            sha, when = line.split(" ", 1)
            ts = datetime.fromisoformat(when).astimezone(TZ)
        except ValueError:
            continue
        zone, rid = None, None
        try:
            js = run(["git", "-C", str(root), "show", f"{sha}:app/readiness_v3.json"],
                     capture_output=True, text=True, timeout=30).stdout
            obj = json.loads(js) if js else {}
            zone = (obj.get("decision") or {}).get("zone")
            md = run(["git", "-C", str(root), "show", f"{sha}:app/informe.md"], capture_output=True, text=True, timeout=30).stdout
            rid = next((w.strip("`") for w in md.split() if w.startswith("`GR-")), None)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        items.append({"label": ts.strftime("%d/%m %H:%M"), "zone": zone, "report_id": rid,
                      "url": f"{REPO_URL}/blob/{sha}/app/informe.md"})
    return items


def build_site(root: str | Path = ".", out: str | Path = "_site", history: bool = True) -> dict:
    from .dashboard import render
    from .report import chart_strength
    from .weekly import punctuality
    root, out = Path(root), Path(out)
    result = json.loads((root / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
    try:
        with (root / "history" / "reports.csv").open(encoding="utf-8", newline="") as fh:
            reports = list(csv.DictReader(fh))
    except OSError:
        reports = []
    try:
        crossfit = json.loads((root / "crossfit_insights.json").read_text(encoding="utf-8"))
        rows = ((crossfit.get("muscle_load") or {}).get("strength_exercises")) or []
        cutoff = (date.fromisoformat(result["date"]) - timedelta(days=55)).isoformat()
        strength = chart_strength([r for r in rows if (r.get("date") or "") >= cutoff])
    except (OSError, ValueError):
        strength = None
    gen = datetime.fromisoformat(result["generated_at"]) if result.get("generated_at") else None
    extras = {"pwa": True, "full_report": (root / "app" / "informe_completo.md").exists(), "strength_svg": strength,
              "punctuality": punctuality(reports, date.fromisoformat(result["date"]), gen),
              "history": report_history(root) if history else []}
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render(result, extras), encoding="utf-8")
    (out / "manifest.webmanifest").write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "sw.js").write_text(SERVICE_WORKER, encoding="utf-8")
    for size in (180, 192, 512):
        (out / f"icon-{size}.png").write_bytes(icon_png(size))
    (out / ".nojekyll").write_text("", encoding="utf-8")
    if (root / "app" / "charts").is_dir():
        shutil.copytree(root / "app" / "charts", out / "charts", dirs_exist_ok=True)
    for name in ("informe.md", "informe_semanal.md", "informe_completo.md"):
        if (root / "app" / name).exists():
            shutil.copy(root / "app" / name, out / name)
    full = root / "app" / "informe_completo.md"
    if full.exists():
        from .mdhtml import page
        from .ai_analysis import section
        (out / "informe_completo.html").write_text(page(full.read_text(encoding="utf-8") + section(root)), encoding="utf-8")
    return {"out": str(out), "history": len(extras["history"]), "date": result["date"],
            "generated_at": result.get("generated_at")}
