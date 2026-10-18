"""Validación del endpoint de RPE desde la web (apps_script/RegistroRPEWeb.gs), cargado con Node."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

GS = Path(__file__).resolve().parent / "apps_script" / "RegistroRPEWeb.gs"
DRIVER = """
const fs = require('fs'), vm = require('vm');
const ctx = vm.createContext({console});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8') + '\\n;globalThis.v = rpeWebValidate_;', ctx);
console.log(JSON.stringify(JSON.parse(process.argv[2]).map(p => ctx.v(p, '2026-10-18'))));
"""


def ok(**kw):
    base = {"activity_id": "i198584544", "rpe": "8,5", "date": "2026-10-18", "name": "Fuerza - pierna"}
    return base | kw


@unittest.skipUnless(shutil.which("node"), "Node no disponible")
class Validate(unittest.TestCase):
    def run_cases(self, *cases):
        out = subprocess.run(["node", "-e", DRIVER, str(GS), json.dumps(cases)], capture_output=True,
                             text=True, check=True).stdout
        return json.loads(out)

    def test_valid_row(self):
        r, = self.run_cases(ok(feelings="cansado", notes="sin dolor"))
        self.assertEqual(r["row"], ["2026-10-18", "i198584544", "Fuerza - pierna", 8.5, "cansado", "sin dolor", "2026-10-18", ""])

    def test_rejections(self):
        bad = self.run_cases(ok(activity_id="x1"), ok(rpe="11"), ok(rpe="abc"), ok(rpe="7,3"), ok(date="18/10/2026"))
        self.assertTrue(all("error" in b for b in bad), bad)

    def test_formula_injection_is_neutralised(self):
        r, = self.run_cases(ok(notes="=IMPORTXML(\"x\")", name="+cmd"))
        self.assertEqual(r["row"][5][0], "'")
        self.assertEqual(r["row"][2][0], "'")

    def test_endpoint_requires_token_and_never_deletes(self):
        src = GS.read_text(encoding="utf-8")
        self.assertIn("Clave incorrecta", src)
        for forbidden in ("deleteRow", "clearContent", "clear(", "deleteRows"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
