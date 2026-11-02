"""Installs the Ilha cursor schemes for the current user and applies one of them.

    python install.py                  # installs both schemes and applies the black one
    python install.py --variant white  # applies the white one
    python install.py --register-only  # only adds both to Mouse settings > Pointers, changes nothing
    python install.py --uninstall      # puts back the pointers that were in use before the first install

Run it from a regular terminal: a process started inside the Claude app (MSIX) may write to a
virtualised registry and folder that the rest of Windows never sees.
"""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
TARGET = Path(os.environ["USERPROFILE"]) / ".ilha-cursors"
BACKUP = TARGET / "backup.json"
CURSORS_KEY = r"Control Panel\Cursors"
SCHEMES_KEY = CURSORS_KEY + r"\Schemes"
SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE, SPIF_SENDCHANGE = 0x01, 0x02


class WindowsRegistry:
    """The few HKCU operations the installer needs; tests swap it for a dict."""

    def read_all(self, path):
        values = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                i = 0
                while True:
                    try:
                        name, data, kind = winreg.EnumValue(key, i)
                    except OSError:
                        break
                    values[name] = (data, kind)
                    i += 1
        except FileNotFoundError:
            pass
        return values

    def write(self, path, name, data, kind):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, kind, data)

    def delete(self, path, name):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass

    def reload_cursors(self):
        if not ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None,
                                                          SPIF_UPDATEINIFILE | SPIF_SENDCHANGE):
            raise OSError("SystemParametersInfo(SPI_SETCURSORS) failed")


def scheme_paths(manifest, variant, target):
    scheme = manifest["schemes"][variant]
    return [str(target / variant / scheme["files"][role]) for role in manifest["order"]]


def copy_files(manifest, target):
    for variant in manifest["schemes"]:
        dest = target / variant
        dest.mkdir(parents=True, exist_ok=True)
        for name in manifest["schemes"][variant]["files"].values():
            shutil.copy2(BUILD / variant / name, dest / name)


def save_backup(reg, manifest, backup_path):
    if backup_path.exists():
        return  # keep the pointers from before the very first install
    current = reg.read_all(CURSORS_KEY)
    keep = {name: [data, kind] for name, (data, kind) in current.items()
            if name in manifest["order"] or name in ("", "Scheme Source")}
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8")


def register(reg, manifest, target):
    for variant, scheme in manifest["schemes"].items():
        reg.write(SCHEMES_KEY, scheme["name"], ",".join(scheme_paths(manifest, variant, target)),
                  winreg.REG_EXPAND_SZ)


def apply(reg, manifest, variant, target):
    for role, path in zip(manifest["order"], scheme_paths(manifest, variant, target)):
        reg.write(CURSORS_KEY, role, path, winreg.REG_EXPAND_SZ)
    reg.write(CURSORS_KEY, "", manifest["schemes"][variant]["name"], winreg.REG_SZ)
    reg.write(CURSORS_KEY, "Scheme Source", 1, winreg.REG_DWORD)  # 1 = user scheme
    reg.reload_cursors()


def uninstall(reg, manifest, backup_path):
    if backup_path.exists():
        saved = json.loads(backup_path.read_text(encoding="utf-8"))
    else:
        saved = {"": ["Windows Default", winreg.REG_SZ], "Scheme Source": [2, winreg.REG_DWORD]}
    for role in manifest["order"]:
        if role in saved:
            reg.write(CURSORS_KEY, role, saved[role][0], saved[role][1])
        else:
            reg.write(CURSORS_KEY, role, "", winreg.REG_EXPAND_SZ)  # empty = the system default pointer
    for name in ("", "Scheme Source"):
        if name in saved:
            reg.write(CURSORS_KEY, name, saved[name][0], saved[name][1])
    for scheme in manifest["schemes"].values():
        reg.delete(SCHEMES_KEY, scheme["name"])
    reg.reload_cursors()


def load_manifest():
    path = BUILD / "manifest.json"
    if not path.exists():
        subprocess.run([sys.executable, str(ROOT / "generate.py")], check=True)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    missing = [v for v in ("black", "white") if v not in manifest["schemes"]]
    if missing:
        subprocess.run([sys.executable, str(ROOT / "generate.py")], check=True)
        manifest = json.loads(path.read_text(encoding="utf-8"))
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", choices=["black", "white"], default="black")
    ap.add_argument("--register-only", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    reg = WindowsRegistry()
    manifest = load_manifest()

    if args.uninstall:
        uninstall(reg, manifest, BACKUP)
        print("Ponteiros de antes devolvidos. A pasta", TARGET, "pode ser apagada.")
        return

    copy_files(manifest, TARGET)
    save_backup(reg, manifest, BACKUP)
    register(reg, manifest, TARGET)
    names = [s["name"] for s in manifest["schemes"].values()]
    if args.register_only:
        print("Esquemas", " e ".join(names), "prontos em Configurações > Mouse > Ponteiros.")
        return
    apply(reg, manifest, args.variant, TARGET)
    print("Aplicado:", manifest["schemes"][args.variant]["name"])


if __name__ == "__main__":
    main()
