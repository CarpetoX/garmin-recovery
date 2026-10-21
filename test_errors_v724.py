"""V7.24: ningún `except Exception` del paquete se traga un error en silencio."""
import ast
import json
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent / "garmin_recovery"
LOUD = ("failed(", "print(", "raise", "warning", "error", "logger", "append(")


def silent_handlers():
    out = []
    for f in sorted(PKG.glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) \
                    and node.type.id in ("Exception", "BaseException"):
                body = ast.unparse(node.body)
                if not ((node.name and node.name in body) or any(k in body for k in LOUD)):
                    out.append(f"{f.name}:{node.lineno}")
    return out


class NoSilentBroadExcept(unittest.TestCase):
    def test_every_broad_handler_reports(self):
        self.assertEqual(silent_handlers(), [], "usa una excepción concreta o registra el fallo (optional_blocks.failed)")


class WebFailuresAreVisible(unittest.TestCase):
    def test_site_writes_status_and_footer(self):
        from garmin_recovery import optional_blocks
        from garmin_recovery.dashboard import render
        root = Path(__file__).resolve().parent
        result = json.loads((root / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        page = render(result, {"web_failures": [{"block": "web:prueba", "error": "ValueError"}]})
        self.assertIn('"web_failures"', page)
        self.assertIn("Bloques no disponibles en esta publicación", page)
        from garmin_recovery.site import build_site
        with tempfile.TemporaryDirectory() as d:
            build_site(root, d, history=False)
            status = json.loads((Path(d) / "estado_web.json").read_text(encoding="utf-8"))
            self.assertIsInstance(status["optional_failures"], list)
        optional_blocks.reset()


if __name__ == "__main__":
    unittest.main()
