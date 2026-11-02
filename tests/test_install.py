"""Installer logic against a fake registry: nothing on the real system is touched."""

import json
import sys
import tempfile
import unittest
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import install  # noqa: E402
from ilhacursors.shapes import CURSORS, SCHEME_ORDER  # noqa: E402

AERO = r"%SystemRoot%\cursors\aero_arrow.cur"


class FakeRegistry:
    def __init__(self, cursors):
        self.keys = {install.CURSORS_KEY: dict(cursors), install.SCHEMES_KEY: {}}
        self.reloads = 0

    def read_all(self, path):
        return dict(self.keys.get(path, {}))

    def write(self, path, name, data, kind):
        self.keys.setdefault(path, {})[name] = (data, kind)

    def delete(self, path, name):
        self.keys.get(path, {}).pop(name, None)

    def reload_cursors(self):
        self.reloads += 1


def manifest():
    files = {c.role: c.file + (".ani" if c.animated else ".cur") for c in CURSORS}
    return {"order": SCHEME_ORDER, "schemes": {"black": {"name": "Ilha preto", "files": files},
                                               "white": {"name": "Ilha branco", "files": files}}}


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.backup = self.tmp / "backup.json"
        self.reg = FakeRegistry({"": ("Windows Default", winreg.REG_SZ), "Arrow": (AERO, winreg.REG_EXPAND_SZ),
                                 "Scheme Source": (2, winreg.REG_DWORD)})
        self.m = manifest()

    def test_every_role_has_a_cursor_in_scheme_order(self):
        self.assertEqual(sorted(SCHEME_ORDER), sorted(c.role for c in CURSORS))
        self.assertEqual(len(SCHEME_ORDER), 17)

    def test_apply_sets_all_roles_and_the_scheme(self):
        install.save_backup(self.reg, self.m, self.backup)
        install.register(self.reg, self.m, self.tmp)
        install.apply(self.reg, self.m, "white", self.tmp)
        cur = self.reg.keys[install.CURSORS_KEY]
        self.assertEqual(cur[""][0], "Ilha branco")
        self.assertEqual(cur["Wait"][0], str(self.tmp / "white" / "busy.ani"))
        self.assertTrue(all(cur[role][0].startswith(str(self.tmp / "white")) for role in SCHEME_ORDER))
        schemes = self.reg.keys[install.SCHEMES_KEY]
        self.assertEqual(schemes["Ilha preto"][0].split(",")[0], str(self.tmp / "black" / "arrow.cur"))
        self.assertEqual(len(schemes["Ilha branco"][0].split(",")), 17)
        self.assertEqual(self.reg.reloads, 1)

    def test_uninstall_restores_what_was_there_before(self):
        install.save_backup(self.reg, self.m, self.backup)
        install.register(self.reg, self.m, self.tmp)
        install.apply(self.reg, self.m, "black", self.tmp)
        install.save_backup(self.reg, self.m, self.backup)  # a second install must not overwrite the backup
        install.uninstall(self.reg, self.m, self.backup)
        cur = self.reg.keys[install.CURSORS_KEY]
        self.assertEqual(cur["Arrow"][0], AERO)
        self.assertEqual(cur[""][0], "Windows Default")
        self.assertEqual(cur["Scheme Source"][0], 2)
        self.assertEqual(cur["Wait"][0], "")
        self.assertEqual(self.reg.keys[install.SCHEMES_KEY], {})
        self.assertEqual(json.loads(self.backup.read_text(encoding="utf-8"))["Arrow"][0], AERO)


if __name__ == "__main__":
    unittest.main()
