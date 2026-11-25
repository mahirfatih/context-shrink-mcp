#!/usr/bin/env python3
"""Run the kebab-case test suites for context-shrink-mcp."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

TEST_DIR = pathlib.Path(__file__).resolve().parent

SUITES = {
    "smoke": "test-smoke.py",
    "sanity": "test-sanity.py",
    "unit": "test-unit.py",
    "regression": "test-regression.py",
    "integration": "test-integration.py",
    "e2e": "test-e2e.py",
    "ui": "test-automated-ui.py",
}


def load_suite(path: pathlib.Path) -> unittest.TestSuite:
    name = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def main(argv: list[str]) -> int:
    names = argv if argv else list(SUITES)
    unknown = [name for name in names if name not in SUITES]
    if unknown:
        print(f"ERROR: unknown suite(s): {unknown}. Choose from {list(SUITES)}", file=sys.stderr)
        return 2

    suite = unittest.TestSuite()
    for name in names:
        suite.addTests(load_suite(TEST_DIR / SUITES[name]))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
