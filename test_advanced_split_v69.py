"""advanced.py reparte las funciones puras en módulos propios y las reexporta (mismos objetos)."""
import ast
import importlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTS = ("advanced_core", "advanced_context", "advanced_hrr", "advanced_models")


class AdvancedSplit(unittest.TestCase):
    def test_facade_reexports_the_same_objects(self):
        adv = importlib.import_module("garmin_recovery.advanced")
        for part in PARTS:
            mod = importlib.import_module(f"garmin_recovery.{part}")
            names = [n.name for n in ast.parse((ROOT / "garmin_recovery" / f"{part}.py").read_text()).body
                     if isinstance(n, ast.FunctionDef)]
            self.assertTrue(names, part)
            for name in names:
                self.assertIs(getattr(adv, name), getattr(mod, name), f"{part}.{name}")

    def test_parts_do_not_depend_on_the_clock(self):
        # NOW y TODAY se sustituyen en los tests sobre advanced: los módulos puros no pueden leerlos
        for part in PARTS:
            text = (ROOT / "garmin_recovery" / f"{part}.py").read_text()
            names = {n.id for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Name)}
            self.assertFalse(names & {"NOW", "TODAY"}, part)
            self.assertNotIn("datetime.now(", text, part)

    def test_layers_only_import_downwards(self):
        for i, part in enumerate(PARTS):
            text = (ROOT / "garmin_recovery" / f"{part}.py").read_text()
            for later in PARTS[i:]:
                self.assertNotIn(f"from .{later} import", text, f"{part} -> {later}")


if __name__ == "__main__":
    unittest.main()
