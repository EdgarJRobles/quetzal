# SPDX-License-Identifier: LGPL-3.0-or-later
"""Static guards for forms that must receive FormServices."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORMS = {
    "pForms.py": ("insertPipeForm",),
    "fFeatures.py": ("insertSectForm", "frameBranchForm"),
}


def _class_node(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"class {name} not found")


def _init_node(class_node):
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            return node
    raise AssertionError(f"{class_node.name} has no __init__")


def _has_services_assignment(init):
    for node in ast.walk(init):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr == "services"
            ):
                return True
    return False


def _passes_services_to_super(init):
    for node in ast.walk(init):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "__init__":
            continue
        if any(keyword.arg == "services" for keyword in node.keywords):
            return True
    return False


def test_injected_forms_keep_the_services_wiring():
    for filename, class_names in FORMS.items():
        tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
        for class_name in class_names:
            init = _init_node(_class_node(tree, class_name))
            args = [arg.arg for arg in init.args.args]
            assert "services" in args, f"{class_name}.__init__ must accept services"
            assert _has_services_assignment(init) or _passes_services_to_super(init), (
                f"{class_name} must assign self.services or pass services to super"
            )
