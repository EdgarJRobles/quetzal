# SPDX-License-Identifier: LGPL-3.0-or-later
"""Headless integration checks for the Quetzal workbench.

Run with::

    freecadcmd tests/integration/freecad_check.py

The script exits with a non-zero status when a feature cannot be built,
cannot be saved/reloaded, or when the catalogue is unreadable.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import FreeCAD  # noqa: E402
import FreeCADGui  # noqa: E402

import pCmd  # noqa: E402
import pFeatures  # noqa: E402
from quetzal.features import FEATURES  # noqa: E402
from quetzal.infrastructure.catalog import default_catalog_repository, tablez_dir  # noqa: E402

FAILURES = []


def check(label, fn):
    try:
        value = fn()
        print(f"ok   {label}", flush=True)
        return value
    except Exception as exc:  # noqa: BLE001 - report every failure
        FAILURES.append((label, exc))
        print(f"FAIL {label}: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        return None


def make(name, factory, require_shape=True, require_ptype=True):
    def build():
        obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
        factory(obj)
        FreeCAD.ActiveDocument.recompute()
        if require_shape:
            shape = getattr(obj, "Shape", None)
            assert shape is not None, "proxy did not create a Shape"
            assert shape.isValid(), "shape is not valid"
        if require_ptype:
            assert obj.PType, "proxy did not set PType"
        return obj

    return build


def check_command_contract():
    """Every registered command must be unique and point to an existing icon."""

    registered = {}
    original = getattr(FreeCADGui, "addCommand", None)

    def fake_add_command(name, command, source=None):
        registered.setdefault(name, []).append(command)

    FreeCADGui.addCommand = fake_add_command
    try:
        for module in ("CPipe", "CFrame", "CUtils", "cut_list.cut_list_commands"):
            importlib.import_module(module)
    finally:
        if original is None:
            delattr(FreeCADGui, "addCommand")
        else:
            FreeCADGui.addCommand = original

    duplicates = {name: len(items) for name, items in registered.items() if len(items) > 1}
    assert not duplicates, f"duplicate commands: {duplicates}"

    from quetzal_config import get_icon_path

    missing_icons = []
    for name, commands in registered.items():
        resources = commands[0].GetResources()
        pixmap = resources.get("Pixmap")
        if pixmap and not os.path.exists(get_icon_path(pixmap)):
            missing_icons.append((name, pixmap))
    assert not missing_icons, f"missing icons: {missing_icons}"

    init_gui = (Path(ROOT) / "InitGui.py").read_text(encoding="utf-8")
    referenced = set(re.findall(r'"(Quetzal_[A-Za-z0-9_]+)"', init_gui))
    orphaned = sorted(referenced - set(registered))
    assert not orphaned, f"InitGui references unregistered commands: {orphaned}"

    return len(registered), len(referenced)


def check_insertion_flows():
    """The legacy ``do*`` command flows must build valid objects headlessly."""

    flows = {
        "pipe": lambda: pCmd.doPipes("SCH-STD", ["DN50", 60.32, 3, 1000]),
        "cap": lambda: pCmd.doCaps("SCH-STD", ["DN50", 60.32, 3]),
        "tee": lambda: pCmd.doTees("SCH-STD", ["DN50", 60.32, 60.32, 3, 3, 100, 100]),
        "flange": lambda: pCmd.doFlanges("DIN-PN16"),
        "reduct": lambda: pCmd.doReduct("SCH-STD", ["DN50", 60.32, 48.3, 3, 3, 100]),
        "gasket": lambda: pCmd.doGaskets(["DN50", "150lb", 55.6, 69.9, 85.9, 104.9, 4.5, 3.2]),
        "bolts": lambda: pCmd.doBolts_Nuts([]),
        "elbow": lambda: pCmd.doElbow("SCH-STD"),
        "valve": lambda: pCmd.doValves(),
    }
    flow_document = FreeCAD.newDocument("quetzal_flows")
    try:
        created = 0
        for label, flow in flows.items():
            objects = flow()
            flow_document.recompute()
            assert objects, f"{label} created no objects"
            for obj in objects:
                assert getattr(obj, "Shape", None) is not None, f"{label} has no shape"
                assert obj.Shape.isValid(), f"{label} produced an invalid shape"
                created += 1
        return created
    finally:
        FreeCAD.closeDocument(flow_document.Name)


def main():
    print(f"FreeCAD {FreeCAD.Version()[0]}.{FreeCAD.Version()[1]}", flush=True)
    document = FreeCAD.newDocument("quetzal_integration")

    cases = [
        ("Pipe", lambda o: pFeatures.Pipe(o, "SCH-STD")),
        ("TerminalAdapter", lambda o: pFeatures.TerminalAdapter(o, "SCH-40")),
        ("Elbow", lambda o: pFeatures.Elbow(o, "SCH-STD")),
        ("DuctElbow", lambda o: pFeatures.DuctElbow(o, "Rectangular")),
        ("Flange", lambda o: pFeatures.Flange(o, "DIN-PN16")),
        ("SocketEll", lambda o: pFeatures.SocketEll(o, "3000lb")),
        ("Tee", lambda o: pFeatures.Tee(o, "SCH-STD")),
        ("SocketTee", lambda o: pFeatures.SocketTee(o, "3000lb")),
        ("Reduct", lambda o: pFeatures.Reduct(o, "SCH-STD")),
        ("DuctReduction", lambda o: pFeatures.DuctReduction(o, "Rectangular")),
        ("Cap", lambda o: pFeatures.Cap(o, "SCH-STD")),
        ("Ubolt", lambda o: pFeatures.Ubolt(o)),
        ("BeamClamp", lambda o: pFeatures.BeamClamp(o)),
        ("Shell", lambda o: pFeatures.Shell(o)),  # legacy: no PType yet
        ("Valve", lambda o: pFeatures.Valve(o)),
        ("Gasket", lambda o: pFeatures.Gasket(o, "150lb")),
        ("Bolts_Nuts", lambda o: pFeatures.Bolts_Nuts(o, "150lb")),
        ("Outlet", lambda o: pFeatures.Outlet(o, "SCH-STD")),
        ("SocketCap", lambda o: pFeatures.SocketCap(o)),
        ("SocketCoupling", lambda o: pFeatures.SocketCoupling(o)),
        ("SocketUnion", lambda o: pFeatures.SocketUnion(o)),
        ("PypeLine2", lambda o: pFeatures.PypeLine2(o, "SCH-STD")),  # meta object
    ]

    built = {}
    for index, (name, factory) in enumerate(cases):
        flags = {}
        if name == "Shell":
            flags["require_ptype"] = False
        if name == "PypeLine2":
            flags["require_shape"] = False
        obj = check(f"build {name}", make(f"{name}{index}", factory, **flags))
        if obj is not None:
            built[name] = obj

    # Public module aliases used by saved documents and third-party macros.
    for attr in ("Pipe", "Cap", "pypeType"):
        check(f"pFeatures.{attr} exists", lambda attr=attr: getattr(pFeatures, attr))

    # Generic registry entries produce the same classes.
    for key in ("Pipe", "Cap", "TerminalAdapter"):
        check(f"registry {key}", lambda key=key: FEATURES.get(key))

    def reads_every_catalogue():
        repo = default_catalog_repository()
        filenames = sorted(p.name for p in tablez_dir().glob("*.csv"))
        assert len(filenames) > 200, f"only {len(filenames)} catalogue files found"
        for filename in filenames:
            table = repo.read_file(filename)
            assert len(table) > 0, f"{filename} is empty"
        return len(filenames)

    count = check("read all catalogues", reads_every_catalogue)
    if count:
        print(f"     catalogues read: {count}", flush=True)

    # Save / reload: verifies that proxy module paths survive serialization.
    def save_and_reload():
        handle, path = tempfile.mkstemp(suffix=".FCStd", dir=ROOT)
        os.close(handle)
        try:
            document.saveAs(path)
            FreeCAD.closeDocument(document.Name)
            reopened = FreeCAD.openDocument(path)
            reopened.recompute()
            types = {obj.PType for obj in reopened.Objects if hasattr(obj, "PType")}
            assert "Pipe" in types, "Pipe lost after reload"
            assert "Cap" in types, "Cap lost after reload"
            for obj in reopened.Objects:
                if hasattr(obj, "PType"):
                    assert obj.Proxy is not None, f"proxy lost for {obj.Name}"
            FreeCAD.closeDocument(reopened.Name)
            return len(types)
        finally:
            if os.path.exists(path):
                os.remove(path)

    check("save and reload document", save_and_reload)
    counts = check("command contract", check_command_contract)
    if counts:
        print(f"     commands registered/referenced: {counts[0]}/{counts[1]}", flush=True)

    flow_count = check("headless insertion flows", check_insertion_flows)
    if flow_count:
        print(f"     objects created by flows: {flow_count}", flush=True)

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)", flush=True)
        return 1
    print("\nall integration checks passed", flush=True)
    return 0


if __name__ in ("__main__", os.path.splitext(os.path.basename(__file__))[0]):
    sys.exit(main())
