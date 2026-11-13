"""Ejecuta con unittest las pruebas escritas como funciones sueltas (estilo pytest).

`python -m unittest discover` solo recoge clases TestCase, así que las funciones `test_*` a nivel de módulo
no se ejecutaban en CI. Este módulo las busca en todos los test_*.py y las convierte en casos de unittest.
Solo admite el fixture `tmp_path` (un directorio temporal nuevo por prueba); cualquier otro parámetro falla
de forma explícita para que no pase desapercibido.
"""
from __future__ import annotations

import importlib
import inspect
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPPORTED = {"tmp_path"}


def _plain_tests():
    for path in sorted(HERE.glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        module = importlib.import_module(path.stem)
        for name, fn in sorted(vars(module).items()):
            if name.startswith("test_") and inspect.isfunction(fn) and fn.__module__ == module.__name__:
                yield path.stem, name, fn


def _case(fn):
    params = list(inspect.signature(fn).parameters)

    def run():
        unknown = [p for p in params if p not in SUPPORTED]
        if unknown:
            raise TypeError(f"{fn.__module__}.{fn.__name__}: fixture no soportado {unknown}")
        if params:
            with tempfile.TemporaryDirectory() as tmp:
                fn(**{p: Path(tmp) for p in params})
        else:
            fn()

    return unittest.FunctionTestCase(run, description=f"{fn.__module__}.{fn.__name__}")


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite(standard_tests)
    for _mod, _name, fn in _plain_tests():
        suite.addTest(_case(fn))
    return suite


class PlainFunctionsDiscovered(unittest.TestCase):
    def test_some_plain_tests_exist(self):
        self.assertGreaterEqual(sum(1 for _ in _plain_tests()), 40)
